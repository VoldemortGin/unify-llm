"""Anthropic 的 OpenAI 兼容端点(独立 adapter)。

形状几乎与 OpenAI 兼容族一致,唯一差异是鉴权头用 ``x-api-key`` 而非 ``Authorization: Bearer``,
故不并入 OPENAI_COMPAT_SPECS,而是薄薄继承 OpenAICompatibleProvider 并覆写头。与原生
AnthropicProvider(Messages API)区别开:这里走 OpenAI 风格的 /chat/completions。
"""

from typing import override

import httpx

from unify_llm.adapters.openai_compatible import OpenAICompatibleProvider, OpenAICompatSpec
from unify_llm.models import ProviderConfig

_SPEC = OpenAICompatSpec(
    name="anthropic_openai",
    base_url="https://api.anthropic.com/v1",
    env_var="ANTHROPIC_API_KEY",
    default_model="claude-sonnet-4-5",
)


class AnthropicOpenAIProvider(OpenAICompatibleProvider):
    """用 OpenAI 风格 API 调 Claude;鉴权头为 x-api-key。"""

    def __init__(
        self,
        config: ProviderConfig,
        *,
        client: httpx.Client | None = None,
        async_client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(config, _SPEC, client=client, async_client=async_client)

    @override
    def _get_headers(self) -> dict[str, str]:
        """x-api-key 鉴权(Anthropic 风格)+ 用户附加头。"""
        headers: dict[str, str] = {"Content-Type": "application/json"}

        if self.config.api_key:
            headers["x-api-key"] = self.config.api_key

        headers.update(self.config.extra_headers)

        return headers
