"""Anthropic (Claude) native Messages API adapter.

把旧 ``providers.anthropic`` 迁入新 adapters 层并纳入严格类型门:行为逐字保持(system 抽到
``system`` 字段、max_tokens 默认 4096、stop_sequences、metadata.user_id、content-block 文本拼接、
SSE 事件分流),只做现代化(无 ``from __future__``、``collections.abc`` 迭代器、PEP604、parse-don't-
validate 私有 pydantic 契约、``@override``、三分支错误归一)。

Anthropic 的 stop_reason(``end_turn`` / ``max_tokens`` / ``tool_use`` / ``stop_sequence``)不是
统一 ``FinishReason`` 的成员,直接塞字段会 ValidationError;故经 ``to_finish_reason`` +
``_ANTHROPIC_FINISH`` 安全归一。
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

# Anthropic 私有 stop_reason → 统一 FinishReason(未命中由 to_finish_reason 兜底为 None)。
_ANTHROPIC_FINISH: dict[str, FinishReason] = {
    "end_turn": FinishReason.STOP,
    "max_tokens": FinishReason.LENGTH,
    "tool_use": FinishReason.TOOL_CALLS,
    "stop_sequence": FinishReason.STOP,
}


# ── parse-don't-validate:Anthropic Messages API 的最小 pydantic 契约 ──────────
class _RawContentBlock(BaseModel):
    """响应 content 数组里的单个内容块(仅关心 text 块)。"""

    type: str = ""
    text: str = ""


class _RawUsage(BaseModel):
    """响应里的 token 计数(输入 / 输出)。"""

    input_tokens: int = 0
    output_tokens: int = 0


class _RawResponse(BaseModel):
    """Messages API 非流式响应的最小契约。"""

    id: str = ""
    model: str = ""
    content: list[_RawContentBlock] = Field(default_factory=list)
    stop_reason: str | None = None
    usage: _RawUsage = Field(default_factory=_RawUsage)


class _RawStreamDelta(BaseModel):
    """流式事件里的 delta 对象(content_block_delta 用 type/text;message_delta 用 stop_reason)。"""

    type: str | None = None
    text: str = ""
    stop_reason: str | None = None


class _RawStreamMessage(BaseModel):
    """流式事件里(可选)携带的 message 元信息(旧实现从此读 id/model,缺省即空串)。"""

    id: str = ""
    model: str = ""


class _RawStreamEvent(BaseModel):
    """Anthropic SSE 事件的最小契约(event-typed:靠 ``type`` 分流)。"""

    type: str | None = None
    delta: _RawStreamDelta = Field(default_factory=_RawStreamDelta)
    message: _RawStreamMessage = Field(default_factory=_RawStreamMessage)


class AnthropicProvider(BaseProvider):
    """Anthropic API provider implementation.

    Supports Claude 3 models (Opus, Sonnet, Haiku) and Claude 2.
    """

    @override
    def _get_headers(self) -> dict[str, str]:
        """Get headers for Anthropic API requests."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",  # API version
        }

        if self.config.api_key:
            headers["x-api-key"] = self.config.api_key

        # Add any extra headers
        headers.update(self.config.extra_headers)

        return headers

    @override
    def _get_base_url(self) -> str:
        """Get the base URL for Anthropic API."""
        return self.config.base_url or "https://api.anthropic.com/v1"

    @override
    def _convert_request(self, request: ChatRequest) -> dict[str, object]:
        """Convert ChatRequest to Anthropic API format.

        Anthropic API has a different format:
        - System messages are a separate parameter
        - Only user and assistant messages in the messages array
        """
        # Separate system messages from other messages
        system_messages: list[str] = []
        conversation_messages: list[dict[str, object]] = []

        for msg in request.messages:
            if msg.role == Role.SYSTEM:
                if msg.content:
                    system_messages.append(msg.content)
            else:
                conversation_messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content or "",
                    }
                )

        payload: dict[str, object] = {
            "model": request.model,
            "messages": conversation_messages,
            "max_tokens": request.max_tokens or 4096,  # Required for Anthropic
            "stream": request.stream,
        }

        # Add system message if present
        if system_messages:
            payload["system"] = "\n\n".join(system_messages)

        # Add optional parameters
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        if request.top_p is not None:
            payload["top_p"] = request.top_p

        if request.stop is not None:
            payload["stop_sequences"] = (
                [request.stop] if isinstance(request.stop, str) else request.stop
            )

        # Anthropic uses "metadata" for user tracking
        if request.user:
            payload["metadata"] = {"user_id": request.user}

        # Add extra parameters
        payload.update(request.extra_params)

        return payload

    @override
    def _convert_response(self, response: dict[str, object]) -> ChatResponse:
        """Convert Anthropic API response to ChatResponse (parse-don't-validate)."""
        parsed = _RawResponse.model_validate(response)

        # Extract text from content blocks
        content = "".join(block.text for block in parsed.content if block.type == "text")

        message = Message(
            role=Role.ASSISTANT,
            content=content,
        )

        choice = ChatResponseChoice(
            index=0,
            message=message,
            finish_reason=to_finish_reason(parsed.stop_reason, mapping=_ANTHROPIC_FINISH),
        )

        usage = Usage(
            prompt_tokens=parsed.usage.input_tokens,
            completion_tokens=parsed.usage.output_tokens,
            total_tokens=parsed.usage.input_tokens + parsed.usage.output_tokens,
        )

        return ChatResponse(
            id=parsed.id,
            model=parsed.model,
            choices=[choice],
            usage=usage,
            created=int(time.time()),
            provider="anthropic",
            raw_response=response,
        )

    @override
    def _convert_stream_chunk(self, chunk: dict[str, object]) -> StreamChunk | None:
        """Convert Anthropic stream chunk to StreamChunk (parse-don't-validate).

        Anthropic uses server-sent events with different event types:
        - message_start: Start of message
        - content_block_start: Start of content block
        - content_block_delta: Content delta
        - content_block_stop: End of content block
        - message_delta: Message metadata delta
        - message_stop: End of message
        """
        parsed = _RawStreamEvent.model_validate(chunk)

        # Only process content_block_delta events
        if parsed.type == "content_block_delta":
            if parsed.delta.type == "text_delta":
                content = parsed.delta.text

                delta = MessageDelta(content=content)
                choice = StreamChoiceDelta(index=0, delta=delta)

                return StreamChunk(
                    id=parsed.message.id,
                    model=parsed.message.model,
                    choices=[choice],
                    created=int(time.time()),
                    provider="anthropic",
                )

        # Handle message_delta for finish reason
        elif parsed.type == "message_delta" and parsed.delta.stop_reason:
            finish_reason = to_finish_reason(parsed.delta.stop_reason, mapping=_ANTHROPIC_FINISH)

            delta = MessageDelta()
            choice = StreamChoiceDelta(
                index=0,
                delta=delta,
                finish_reason=finish_reason,
            )

            return StreamChunk(
                id="",
                model="",
                choices=[choice],
                created=int(time.time()),
                provider="anthropic",
            )

        return None

    @override
    def _chat_impl(self, request: ChatRequest) -> ChatResponse:
        """Implementation of synchronous chat request."""
        url = f"{self._get_base_url()}/messages"
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
        url = f"{self._get_base_url()}/messages"
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
        url = f"{self._get_base_url()}/messages"
        payload = self._convert_request(request)

        try:
            with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line.strip():
                        continue

                    # Anthropic uses "event: " and "data: " format
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix

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
        url = f"{self._get_base_url()}/messages"
        payload = self._convert_request(request)

        try:
            async with self.async_client.stream("POST", url, json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix

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
