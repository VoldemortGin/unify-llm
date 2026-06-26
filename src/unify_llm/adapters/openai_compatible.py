"""OpenAI 兼容族(ADR-07):一个 OpenAICompatibleProvider + 一张数据注册表。

把 openai / grok / openrouter / bytedance / deepseek 这些"逐字段 OpenAI 兼容"的厂商收敛成
同一份转换逻辑,差异只剩 base_url / 鉴权 env / 默认 model / 少量开关,统统下沉到
``OPENAI_COMPAT_SPECS`` 数据表。新增一个兼容厂商 = 加一行 spec,不再复制一个类。

每个具名子类(OpenAIProvider 等)只是把对应 spec 绑死,既保持 ``unify_llm.providers.X``
的向后兼容导入,又让工厂注册表 ``dict[str, type[BaseProvider]]`` 形状统一(均可 ``cls(config)``
构造)。真正的实现只有 OpenAICompatibleProvider 一处。
"""

import json
import time
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import override

import httpx
from pydantic import BaseModel, Field

from unify_llm.adapters.base import BaseProvider
from unify_llm.core.exceptions import TimeoutError as UnifyTimeoutError
from unify_llm.models import (
    ChatRequest,
    ChatResponse,
    ChatResponseChoice,
    FinishReason,
    Message,
    MessageDelta,
    ProviderConfig,
    Role,
    StreamChoiceDelta,
    StreamChunk,
    Usage,
)


@dataclass(frozen=True, slots=True)
class OpenAICompatSpec:
    """一个 OpenAI 兼容厂商的全部差异(数据,而非代码)。

    Attributes:
        name: provider 标识(也用作 ChatResponse.provider 字段)。
        base_url: 默认 base URL(可被 ProviderConfig.base_url 覆盖)。
        env_var: 取 API key 的环境变量名(信息性;实际取键经 utils.get_api_key_from_env)。
        default_model: 文档/演示用默认 model。
        coerce_empty_content: 是否把 None content 序列化成空串(bytedance 历史行为)。
        default_headers: 附加默认头(如 OpenRouter 的 HTTP-Referer / X-Title),用户头优先。
    """

    name: str
    base_url: str
    env_var: str
    default_model: str
    coerce_empty_content: bool = False
    default_headers: dict[str, str] = field(default_factory=dict)


# ── 数据注册表:一行一个兼容厂商(含正式装配的 deepseek)──────────────────────
OPENAI_COMPAT_SPECS: dict[str, OpenAICompatSpec] = {
    "openai": OpenAICompatSpec(
        name="openai",
        base_url="https://api.openai.com/v1",
        env_var="OPENAI_API_KEY",
        default_model="gpt-4o-mini",
    ),
    "grok": OpenAICompatSpec(
        name="grok",
        base_url="https://api.x.ai/v1",
        env_var="XAI_API_KEY",
        default_model="grok-4",
    ),
    "openrouter": OpenAICompatSpec(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        env_var="OPENROUTER_API_KEY",
        default_model="openai/gpt-4o-mini",
        default_headers={
            "HTTP-Referer": "https://github.com/unify-llm",
            "X-Title": "UnifyLLM",
        },
    ),
    "bytedance": OpenAICompatSpec(
        name="bytedance",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        env_var="BYTEDANCE_API_KEY",
        default_model="doubao-pro-4k",
        coerce_empty_content=True,
    ),
    "deepseek": OpenAICompatSpec(
        name="deepseek",
        base_url="https://api.deepseek.com",
        env_var="DEEPSEEK_API_KEY",
        default_model="deepseek-chat",
    ),
}


# ── parse-don't-validate:OpenAI chat-completions 响应的最小 pydantic 契约 ─────
class _RawMessage(BaseModel):
    """响应里的 message 对象。"""

    role: Role = Role.ASSISTANT
    content: str | None = None
    tool_calls: list[dict[str, object]] | None = None


class _RawChoice(BaseModel):
    """非流式响应的单个 choice。"""

    index: int = 0
    message: _RawMessage = Field(default_factory=_RawMessage)
    finish_reason: FinishReason | None = None


class _RawUsage(BaseModel):
    """响应里的 usage 计数。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class _RawResponse(BaseModel):
    """chat completion 原始响应的最小契约。"""

    id: str = ""
    model: str = ""
    choices: list[_RawChoice] = Field(default_factory=list)
    usage: _RawUsage = Field(default_factory=_RawUsage)
    created: int | None = None


class _RawDelta(BaseModel):
    """流式 chunk 里的 delta 对象。"""

    role: Role | None = None
    content: str | None = None
    tool_calls: list[dict[str, object]] | None = None


class _RawStreamChoice(BaseModel):
    """流式 chunk 的单个 choice。"""

    index: int = 0
    delta: _RawDelta = Field(default_factory=_RawDelta)
    finish_reason: FinishReason | None = None


class _RawStreamChunk(BaseModel):
    """流式 chunk 的最小契约。"""

    id: str = ""
    model: str = ""
    choices: list[_RawStreamChoice] = Field(default_factory=list)
    created: int | None = None


class OpenAICompatibleProvider(BaseProvider):
    """所有 OpenAI 兼容厂商共用的实现;差异由注入的 OpenAICompatSpec 表达。"""

    def __init__(self, config: ProviderConfig, spec: OpenAICompatSpec | None = None) -> None:
        """绑定 spec 后再起 HTTP 管线(super().__init__ 会回调 _get_headers,需 spec 先就位)。"""
        self._spec = spec if spec is not None else OPENAI_COMPAT_SPECS["openai"]
        super().__init__(config)
        self.name = self._spec.name

    @override
    def _get_headers(self) -> dict[str, str]:
        """Bearer 鉴权 + 可选 organization + spec 默认头(用户头优先)。"""
        headers: dict[str, str] = {"Content-Type": "application/json"}

        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        if self.config.organization:
            headers["OpenAI-Organization"] = self.config.organization

        headers.update(self.config.extra_headers)

        for key, value in self._spec.default_headers.items():
            headers.setdefault(key, value)

        return headers

    @override
    def _get_base_url(self) -> str:
        """ProviderConfig.base_url 优先,否则取 spec 默认。"""
        return self.config.base_url or self._spec.base_url

    @override
    def _convert_request(self, request: ChatRequest) -> dict[str, object]:
        """Convert ChatRequest to OpenAI-compatible request payload."""
        coerce = self._spec.coerce_empty_content
        payload: dict[str, object] = {
            "model": request.model,
            "messages": [
                {
                    "role": msg.role,
                    "content": (msg.content or "") if coerce else msg.content,
                    **({"name": msg.name} if msg.name else {}),
                    **({"tool_calls": msg.tool_calls} if msg.tool_calls else {}),
                    **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {}),
                }
                for msg in request.messages
            ],
            "stream": request.stream,
        }

        if request.temperature is not None:
            payload["temperature"] = request.temperature

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        if request.top_p is not None:
            payload["top_p"] = request.top_p

        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty

        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty

        if request.stop is not None:
            payload["stop"] = request.stop

        if request.tools is not None:
            payload["tools"] = request.tools

        if request.tool_choice is not None:
            payload["tool_choice"] = request.tool_choice

        if request.response_format is not None:
            payload["response_format"] = request.response_format

        if request.user is not None:
            payload["user"] = request.user

        payload.update(request.extra_params)

        return payload

    @override
    def _convert_response(self, response: dict[str, object]) -> ChatResponse:
        """Convert OpenAI-compatible response to ChatResponse (parse-don't-validate)."""
        parsed = _RawResponse.model_validate(response)

        choices = [
            ChatResponseChoice(
                index=choice.index,
                message=Message(
                    role=choice.message.role,
                    content=choice.message.content,
                    tool_calls=choice.message.tool_calls,
                ),
                finish_reason=choice.finish_reason,
            )
            for choice in parsed.choices
        ]

        usage = Usage(
            prompt_tokens=parsed.usage.prompt_tokens,
            completion_tokens=parsed.usage.completion_tokens,
            total_tokens=parsed.usage.total_tokens,
        )

        return ChatResponse(
            id=parsed.id,
            model=parsed.model,
            choices=choices,
            usage=usage,
            created=parsed.created if parsed.created is not None else int(time.time()),
            provider=self.name,
            raw_response=response,
        )

    @override
    def _convert_stream_chunk(self, chunk: dict[str, object]) -> StreamChunk | None:
        """Convert OpenAI-compatible stream chunk to StreamChunk (parse-don't-validate)."""
        if not chunk:
            return None

        parsed = _RawStreamChunk.model_validate(chunk)

        choices = [
            StreamChoiceDelta(
                index=choice.index,
                delta=MessageDelta(
                    role=choice.delta.role,
                    content=choice.delta.content,
                    tool_calls=choice.delta.tool_calls,
                ),
                finish_reason=choice.finish_reason,
            )
            for choice in parsed.choices
        ]

        if not choices:
            return None

        return StreamChunk(
            id=parsed.id,
            model=parsed.model,
            choices=choices,
            created=parsed.created if parsed.created is not None else int(time.time()),
            provider=self.name,
        )

    @override
    def _chat_impl(self, request: ChatRequest) -> ChatResponse:
        """Implementation of synchronous chat request."""
        url = f"{self._get_base_url()}/chat/completions"
        payload = self._convert_request(request)

        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            return self._convert_response(response.json())
        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider=self.name,
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise
        except httpx.RequestError as e:
            raise self._network_error(e) from e

    @override
    async def _achat_impl(self, request: ChatRequest) -> ChatResponse:
        """Implementation of asynchronous chat request."""
        url = f"{self._get_base_url()}/chat/completions"
        payload = self._convert_request(request)

        try:
            response = await self.async_client.post(url, json=payload)
            response.raise_for_status()
            return self._convert_response(response.json())
        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider=self.name,
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise
        except httpx.RequestError as e:
            raise self._network_error(e) from e

    @override
    def _chat_stream_impl(self, request: ChatRequest) -> Iterator[StreamChunk]:
        """Implementation of synchronous streaming chat request."""
        url = f"{self._get_base_url()}/chat/completions"
        payload = self._convert_request(request)

        try:
            with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line.strip():
                        continue

                    if line.startswith("data: "):
                        data = line[6:]

                        if data.strip() == "[DONE]":
                            break

                        try:
                            chunk_data = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        chunk = self._convert_stream_chunk(chunk_data)
                        if chunk:
                            yield chunk

        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider=self.name,
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise
        except httpx.RequestError as e:
            raise self._network_error(e) from e

    @override
    async def _achat_stream_impl(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """Implementation of asynchronous streaming chat request."""
        url = f"{self._get_base_url()}/chat/completions"
        payload = self._convert_request(request)

        try:
            async with self.async_client.stream("POST", url, json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    if line.startswith("data: "):
                        data = line[6:]

                        if data.strip() == "[DONE]":
                            break

                        try:
                            chunk_data = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        chunk = self._convert_stream_chunk(chunk_data)
                        if chunk:
                            yield chunk

        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider=self.name,
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise
        except httpx.RequestError as e:
            raise self._network_error(e) from e


# ── 具名子类:绑死 spec,保持向后兼容导入 + 统一注册表形状 ────────────────────
class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI(GPT-4o / o-series 等)。"""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config, OPENAI_COMPAT_SPECS["openai"])


class GrokProvider(OpenAICompatibleProvider):
    """xAI Grok(api.x.ai,env XAI_API_KEY)。"""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config, OPENAI_COMPAT_SPECS["grok"])


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter(统一聚合,env OPENROUTER_API_KEY)。"""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config, OPENAI_COMPAT_SPECS["openrouter"])


class ByteDanceProvider(OpenAICompatibleProvider):
    """ByteDance 豆包 / Ark(content 强制非空,env BYTEDANCE_API_KEY)。"""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config, OPENAI_COMPAT_SPECS["bytedance"])


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek(api.deepseek.com,env DEEPSEEK_API_KEY)。"""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config, OPENAI_COMPAT_SPECS["deepseek"])
