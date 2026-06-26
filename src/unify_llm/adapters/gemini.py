"""Google Gemini adapter(generativelanguage v1beta:generateContent)。

把统一的 ChatRequest 翻成 Gemini 的 ``contents``/``parts`` 形状(assistant→model、system 走
``systemInstruction``、采样开关进 ``generationConfig``),并把 ``candidates`` 响应/逐行 JSON 流
解析回统一模型。鉴权用 query 参数 ``?key=``,故另有 ``_get_api_url`` 拼完整 URL。
"""

import json
import time
from collections.abc import AsyncIterator, Iterator
from typing import override

import httpx
from pydantic import BaseModel, Field

from unify_llm.adapters.base import BaseProvider, to_finish_reason
from unify_llm.core.exceptions import TimeoutError as UnifyTimeoutError
from unify_llm.models import (
    ChatRequest,
    ChatResponse,
    ChatResponseChoice,
    FinishReason,
    Message,
    MessageDelta,
    Role,
    StreamChoiceDelta,
    StreamChunk,
    Usage,
)

# Gemini 私有 finishReason → 统一 FinishReason(未知一律 None,绝不做 .lower() 兜底)。
_GEMINI_FINISH: dict[str, FinishReason] = {
    "STOP": FinishReason.STOP,
    "MAX_TOKENS": FinishReason.LENGTH,
    "SAFETY": FinishReason.CONTENT_FILTER,
    "RECITATION": FinishReason.CONTENT_FILTER,
}


# ── parse-don't-validate:Gemini generateContent 响应/流块的最小 pydantic 契约 ──
class _RawPart(BaseModel):
    """``content.parts`` 里的单个文本片段。"""

    text: str = ""


class _RawContent(BaseModel):
    """candidate 的 ``content`` 对象(承载 parts)。"""

    parts: list[_RawPart] = Field(default_factory=list)


class _RawCandidate(BaseModel):
    """单个生成候选(content + finishReason)。"""

    content: _RawContent = Field(default_factory=_RawContent)
    finishReason: str | None = None  # 镜像 Gemini JSON 键名


class _RawUsageMetadata(BaseModel):
    """``usageMetadata`` 计数(流块无此字段,取默认 0)。"""

    promptTokenCount: int = 0  # 镜像 Gemini JSON 键名
    candidatesTokenCount: int = 0  # 镜像 Gemini JSON 键名
    totalTokenCount: int = 0  # 镜像 Gemini JSON 键名


class _RawResponse(BaseModel):
    """generateContent 响应与 streamGenerateContent 流块共用的最小契约。

    流块只带 ``candidates``/``modelVersion``,``usageMetadata`` 缺省即取默认 0,故同一模型复用。
    """

    candidates: list[_RawCandidate] = Field(default_factory=list)
    usageMetadata: _RawUsageMetadata = Field(default_factory=_RawUsageMetadata)  # 镜像 JSON 键名
    modelVersion: str = ""  # 镜像 Gemini JSON 键名


class GeminiProvider(BaseProvider):
    """Google Gemini API provider implementation.

    Supports Gemini Pro, Gemini Pro Vision, and other Gemini models.
    """

    @override
    def _get_headers(self) -> dict[str, str]:
        """Get headers for Gemini API requests."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        headers.update(self.config.extra_headers)
        return headers

    @override
    def _get_base_url(self) -> str:
        """Get the base URL for Gemini API."""
        return self.config.base_url or "https://generativelanguage.googleapis.com/v1beta"

    def _get_api_url(self, model: str, stream: bool = False) -> str:
        """Get the full API URL including the API key.

        Args:
            model: Model name
            stream: Whether this is a streaming request

        Returns:
            Full API URL with key parameter
        """
        base = self._get_base_url()
        method = "streamGenerateContent" if stream else "generateContent"
        url = f"{base}/models/{model}:{method}"

        # Add API key as query parameter
        if self.config.api_key:
            url += f"?key={self.config.api_key}"

        return url

    @override
    def _convert_request(self, request: ChatRequest) -> dict[str, object]:
        """Convert ChatRequest to Gemini API format.

        Gemini API format:
        - Uses "contents" array with "parts" for each message
        - Role can be "user" or "model" (not "assistant")
        - System instructions are separate
        """
        # Separate system messages
        system_instruction: dict[str, object] | None = None
        contents: list[dict[str, object]] = []

        for msg in request.messages:
            if msg.role == Role.SYSTEM:
                # Gemini uses systemInstruction field
                if msg.content:
                    system_instruction = {"parts": [{"text": msg.content}]}
            else:
                # Map "assistant" to "model" for Gemini
                role = "model" if msg.role == Role.ASSISTANT else msg.role
                contents.append(
                    {
                        "role": role,
                        "parts": [{"text": msg.content or ""}],
                    }
                )

        payload: dict[str, object] = {"contents": contents}

        # Add system instruction if present
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        # Generation config
        generation_config: dict[str, object] = {}

        if request.temperature is not None:
            generation_config["temperature"] = request.temperature

        if request.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_tokens

        if request.top_p is not None:
            generation_config["topP"] = request.top_p

        if request.stop is not None:
            stop_sequences = [request.stop] if isinstance(request.stop, str) else request.stop
            generation_config["stopSequences"] = stop_sequences

        if generation_config:
            payload["generationConfig"] = generation_config

        # Add extra parameters
        payload.update(request.extra_params)

        return payload

    @override
    def _convert_response(self, response: dict[str, object]) -> ChatResponse:
        """Convert Gemini API response to ChatResponse (parse-don't-validate)."""
        parsed = _RawResponse.model_validate(response)

        choices = [
            ChatResponseChoice(
                index=i,
                message=Message(
                    role=Role.ASSISTANT,
                    content="".join(part.text for part in candidate.content.parts),
                ),
                finish_reason=to_finish_reason(candidate.finishReason, mapping=_GEMINI_FINISH),
            )
            for i, candidate in enumerate(parsed.candidates)
        ]

        usage = Usage(
            prompt_tokens=parsed.usageMetadata.promptTokenCount,
            completion_tokens=parsed.usageMetadata.candidatesTokenCount,
            total_tokens=parsed.usageMetadata.totalTokenCount,
        )

        return ChatResponse(
            id=parsed.modelVersion,
            model=parsed.modelVersion,
            choices=choices,
            usage=usage,
            created=int(time.time()),
            provider="gemini",
            raw_response=response,
        )

    @override
    def _convert_stream_chunk(self, chunk: dict[str, object]) -> StreamChunk | None:
        """Convert Gemini stream chunk to StreamChunk (parse-don't-validate)."""
        if not chunk:
            return None

        parsed = _RawResponse.model_validate(chunk)
        if not parsed.candidates:
            return None

        choices: list[StreamChoiceDelta] = []
        for i, candidate in enumerate(parsed.candidates):
            content = "".join(part.text for part in candidate.content.parts)
            choices.append(
                StreamChoiceDelta(
                    index=i,
                    delta=MessageDelta(content=content if content else None),
                    finish_reason=to_finish_reason(candidate.finishReason, mapping=_GEMINI_FINISH),
                )
            )

        if not choices:
            return None

        return StreamChunk(
            id=parsed.modelVersion,
            model=parsed.modelVersion,
            choices=choices,
            created=int(time.time()),
            provider="gemini",
        )

    @override
    def _chat_impl(self, request: ChatRequest) -> ChatResponse:
        """Implementation of synchronous chat request."""
        url = self._get_api_url(request.model, stream=False)
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
        url = self._get_api_url(request.model, stream=False)
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
        url = self._get_api_url(request.model, stream=True)
        payload = self._convert_request(request)

        try:
            with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()

                # Gemini streams JSON objects separated by newlines
                for line in response.iter_lines():
                    if not line.strip():
                        continue

                    try:
                        chunk_data = json.loads(line)
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
        url = self._get_api_url(request.model, stream=True)
        payload = self._convert_request(request)

        try:
            async with self.async_client.stream("POST", url, json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    try:
                        chunk_data = json.loads(line)
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
