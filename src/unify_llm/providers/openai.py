"""OpenAI provider implementation."""

import json
import time
from collections.abc import AsyncIterator, Iterator
from typing import override

import httpx
from pydantic import BaseModel, Field

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
from unify_llm.providers.base import BaseProvider


class _RawMessage(BaseModel):
    """parse-don't-validate:OpenAI 响应里的 message 对象(最小契约)。"""

    role: Role = Role.ASSISTANT
    content: str | None = None
    tool_calls: list[dict[str, object]] | None = None


class _RawChoice(BaseModel):
    """OpenAI 非流式响应的单个 choice。"""

    index: int = 0
    message: _RawMessage = Field(default_factory=_RawMessage)
    finish_reason: FinishReason | None = None


class _RawUsage(BaseModel):
    """OpenAI 响应里的 usage 计数。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class _RawResponse(BaseModel):
    """OpenAI chat completion 原始响应的最小 pydantic 契约。"""

    id: str = ""
    model: str = ""
    choices: list[_RawChoice] = Field(default_factory=list)
    usage: _RawUsage = Field(default_factory=_RawUsage)
    created: int | None = None


class _RawDelta(BaseModel):
    """OpenAI 流式 chunk 里的 delta 对象。"""

    role: Role | None = None
    content: str | None = None
    tool_calls: list[dict[str, object]] | None = None


class _RawStreamChoice(BaseModel):
    """OpenAI 流式 chunk 的单个 choice。"""

    index: int = 0
    delta: _RawDelta = Field(default_factory=_RawDelta)
    finish_reason: FinishReason | None = None


class _RawStreamChunk(BaseModel):
    """OpenAI 流式 chunk 的最小 pydantic 契约。"""

    id: str = ""
    model: str = ""
    choices: list[_RawStreamChoice] = Field(default_factory=list)
    created: int | None = None


class OpenAIProvider(BaseProvider):
    """OpenAI API provider implementation.

    Supports GPT-4, GPT-3.5-turbo, and other OpenAI models.
    """

    @override
    def _get_headers(self) -> dict[str, str]:
        """Get headers for OpenAI API requests."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }

        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        if self.config.organization:
            headers["OpenAI-Organization"] = self.config.organization

        # Add any extra headers
        headers.update(self.config.extra_headers)

        return headers

    @override
    def _get_base_url(self) -> str:
        """Get the base URL for OpenAI API."""
        return self.config.base_url or "https://api.openai.com/v1"

    @override
    def _convert_request(self, request: ChatRequest) -> dict[str, object]:
        """Convert ChatRequest to OpenAI API format."""
        payload: dict[str, object] = {
            "model": request.model,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    **({"name": msg.name} if msg.name else {}),
                    **({"tool_calls": msg.tool_calls} if msg.tool_calls else {}),
                    **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {}),
                }
                for msg in request.messages
            ],
            "stream": request.stream,
        }

        # Add optional parameters
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

        # Add extra parameters
        payload.update(request.extra_params)

        return payload

    @override
    def _convert_response(self, response: dict[str, object]) -> ChatResponse:
        """Convert OpenAI API response to ChatResponse (parse-don't-validate)."""
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
            provider="openai",
            raw_response=response,
        )

    @override
    def _convert_stream_chunk(self, chunk: dict[str, object]) -> StreamChunk | None:
        """Convert OpenAI stream chunk to StreamChunk (parse-don't-validate)."""
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
            provider="openai",
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
                provider="openai",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

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
                provider="openai",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

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
                        data = line[6:]  # Remove "data: " prefix

                        if data.strip() == "[DONE]":
                            break

                        try:
                            chunk_data = json.loads(data)
                            chunk = self._convert_stream_chunk(chunk_data)
                            if chunk:
                                yield chunk
                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider="openai",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

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
                        data = line[6:]  # Remove "data: " prefix

                        if data.strip() == "[DONE]":
                            break

                        try:
                            chunk_data = json.loads(data)
                            chunk = self._convert_stream_chunk(chunk_data)
                            if chunk:
                                yield chunk
                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider="openai",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise
