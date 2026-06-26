"""唯一装配缝(ADR-05/06):把"选哪个 provider 实现 + 拿哪个真实 key"集中到一处。

- ``make_llm(provider=None, ...)``:模型无关核心/领域代码用的工厂。按入参或 ``APP_LLM_PROVIDER``
  选实现,真实 key 经注册表从对应 env 取;**无 key 时**非生产回退确定性 MockProvider,
  **生产(APP_ENV==production)缺 key 直接硬失败**(绝不静默回退)。未知 provider → raise。
- ``build(provider, config)``:门面(UnifyLLM)用的纯查表构造,不做 Mock 回退(保持历史语义:
  显式选定的 provider 就如实构造,缺 key 留到调用时报错)。
- ``REGISTRY`` / ``register``:把原 client.UnifyLLM._providers 收编于此,作为唯一 provider 表。
"""

import os
from typing import Protocol, runtime_checkable

import httpx

from unify_llm.adapters.anthropic import AnthropicProvider
from unify_llm.adapters.anthropic_openai import AnthropicOpenAIProvider
from unify_llm.adapters.base import BaseProvider
from unify_llm.adapters.databricks import DatabricksProvider
from unify_llm.adapters.gemini import GeminiProvider
from unify_llm.adapters.mock import MockProvider
from unify_llm.adapters.ollama import OllamaProvider
from unify_llm.adapters.openai_compatible import (
    ByteDanceProvider,
    DeepSeekProvider,
    GrokProvider,
    OpenAIProvider,
    OpenRouterProvider,
)
from unify_llm.adapters.qwen import QwenProvider
from unify_llm.core.exceptions import AuthenticationError, InvalidRequestError
from unify_llm.core.settings import get_settings
from unify_llm.models import ProviderConfig
from unify_llm.ports.llm import LLMProvider
from unify_llm.utils import ENV_VAR_MAP, get_api_key_from_env, requires_api_key


# 一个 builder 接受 ProviderConfig(+ 可选注入的共享 HTTP 客户端)、产出一个满足 LLMProvider
# 的 provider(provider 类即 builder,结构上满足本 Protocol)。Protocol 而非裸 Callable:让具名
# 类的 ``(config, *, client=None, async_client=None)`` 构造签名在 mypy 严格下被结构化接受。
# runtime_checkable:beartype On 时按"是否可调用"对 builder 参数/REGISTRY 值做结构判定。
@runtime_checkable
class ProviderBuilder(Protocol):
    def __call__(
        self,
        config: ProviderConfig,
        *,
        client: httpx.Client | None = None,
        async_client: httpx.AsyncClient | None = None,
    ) -> BaseProvider: ...


# 唯一 provider 注册表(收编自 client.UnifyLLM._providers)。
REGISTRY: dict[str, ProviderBuilder] = {
    "openai": OpenAIProvider,
    "grok": GrokProvider,
    "openrouter": OpenRouterProvider,
    "bytedance": ByteDanceProvider,
    "deepseek": DeepSeekProvider,
    "anthropic": AnthropicProvider,
    "anthropic_openai": AnthropicOpenAIProvider,
    "gemini": GeminiProvider,
    "qwen": QwenProvider,
    "ollama": OllamaProvider,
    "databricks": DatabricksProvider,
}


def register(name: str, builder: ProviderBuilder) -> None:
    """注册/覆盖一个 provider builder(供 UnifyLLM.register_provider 委托)。"""
    REGISTRY[name.lower()] = builder


def available_providers() -> list[str]:
    """已注册的 provider 名(含内置 mock),排序后返回。"""
    return sorted([*REGISTRY, "mock"])


def _unknown(name: str) -> InvalidRequestError:
    available = ", ".join(available_providers())
    return InvalidRequestError(f"Provider '{name}' not supported. Available providers: {available}")


def build(
    provider: str,
    config: ProviderConfig,
    *,
    client: httpx.Client | None = None,
    async_client: httpx.AsyncClient | None = None,
) -> LLMProvider:
    """纯查表构造一个 provider(未知 → raise)。门面用,不做 Mock 回退。

    ``client`` / ``async_client`` 可注入进程级共享 HTTP 客户端(网关用);省略则 provider 自建私有
    客户端并自负关闭。mock → MockProvider(不接受客户端,忽略注入)。
    """
    if provider.lower() == "mock":
        return MockProvider()
    builder = REGISTRY.get(provider.lower())
    if builder is None:
        raise _unknown(provider)
    return builder(config, client=client, async_client=async_client)


def make_llm(
    provider: str | None = None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout: float = 60.0,
    max_retries: int = 3,
    organization: str | None = None,
    extra_headers: dict[str, str] | None = None,
    http_client: httpx.AsyncClient | None = None,
    http_client_sync: httpx.Client | None = None,
) -> LLMProvider:
    """按入参/env 选 provider 并装配;缺 key 时非生产回退 Mock、生产硬失败。

    Args:
        provider: provider 名;None 时取 ``APP_LLM_PROVIDER`` env 或 settings.llm_provider。
        api_key: 显式 key;None 时经注册表从对应 env 取。
        base_url / timeout / max_retries / organization / extra_headers: 透传 ProviderConfig。
        http_client: 可注入的进程级共享异步 HTTP 客户端(网关用,provider 不负责关闭它)。
        http_client_sync: 可注入的同步 HTTP 客户端;省略则 provider 自建私有同步客户端。

    Returns:
        一个满足 LLMProvider 的实现。

    Raises:
        InvalidRequestError: provider 未知。
        AuthenticationError: 生产环境且缺真实 key(硬失败,不回退 Mock)。
    """
    settings = get_settings()
    name = (provider or os.getenv("APP_LLM_PROVIDER") or settings.llm_provider or "mock").lower()

    if name == "mock":
        return MockProvider()

    if name not in REGISTRY:
        raise _unknown(name)

    resolved_key = api_key if api_key is not None else get_api_key_from_env(name)

    if resolved_key is None and requires_api_key(name):
        app_env = os.getenv("APP_ENV", settings.app_env).lower()
        if app_env == "production":
            hint = " / ".join(ENV_VAR_MAP.get(name, [])) or "<provider key>"
            raise AuthenticationError(
                message=(
                    f"No API key for provider '{name}' in production "
                    f"(set one of: {hint}); refusing to fall back to MockProvider"
                ),
                provider=name,
            )
        # 非生产:离线/CI 可跑,回退确定性 Mock。
        return MockProvider()

    config = ProviderConfig(
        api_key=resolved_key,
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        organization=organization,
        extra_headers=extra_headers or {},
    )
    return REGISTRY[name](config, client=http_client_sync, async_client=http_client)
