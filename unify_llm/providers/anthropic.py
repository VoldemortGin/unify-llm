"""Anthropic (Claude) provider implementation."""


from __future__ import annotations

import json
import time
from typing import AsyncIterator, Iterator, Optional

import httpx

from unify_llm.core.exceptions import TimeoutError as UnifyTimeoutError
from unify_llm.models import (
    ChatRequest,
    ChatResponse,
    ChatResponseChoice,
    Message,
    MessageDelta,
    StreamChoiceDelta,
    StreamChunk,
    Usage,
)
from unify_llm.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Anthropic API provider implementation.

    Supports Claude 3 models (Opus, Sonnet, Haiku) and Claude 2.
    """

    def _get_headers(self) -> dict:
        """Get headers for Anthropic API requests."""
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",  # API version
        }

        if self.config.api_key:
            headers["x-api-key"] = self.config.api_key

        # Add any extra headers
        headers.update(self.config.extra_headers)

        return headers

    def _get_base_url(self) -> str:
        """Get the base URL for Anthropic API."""
        return self.config.base_url or "https://api.anthropic.com/v1"

    def _convert_request(self, request: ChatRequest) -> dict:
        """Convert ChatRequest to Anthropic API format.

        Anthropic API has a different format:
        - System messages are a separate parameter
        - Only user and assistant messages in the messages array
        """
        # Separate system messages from other messages
        system_messages = []
        conversation_messages = []

        for msg in request.messages:
            if msg.role == "system":
                if msg.content:
                    system_messages.append(msg.content)
            else:
                conversation_messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content or "",
                    }
                )

        payload = {
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

    def _convert_response(self, response: dict) -> ChatResponse:
        """Convert Anthropic API response to ChatResponse."""
        # Anthropic response format is different
        content_blocks = response.get("content", [])
        content = ""

        # Extract text from content blocks
        for block in content_blocks:
            if block.get("type") == "text":
                content += block.get("text", "")

        message = Message(
            role="assistant",
            content=content,
        )

        choice = ChatResponseChoice(
            index=0,
            message=message,
            finish_reason=response.get("stop_reason"),  # "end_turn", "max_tokens", etc.
        )

        usage_data = response.get("usage", {})
        usage = Usage(
            prompt_tokens=usage_data.get("input_tokens", 0),
            completion_tokens=usage_data.get("output_tokens", 0),
            total_tokens=(usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0)),
        )

        return ChatResponse(
            id=response.get("id", ""),
            model=response.get("model", ""),
            choices=[choice],
            usage=usage,
            created=int(time.time()),
            provider="anthropic",
            raw_response=response,
        )

    def _convert_stream_chunk(self, chunk: dict) -> StreamChunk | None:
        """Convert Anthropic stream chunk to StreamChunk.

        Anthropic uses server-sent events with different event types:
        - message_start: Start of message
        - content_block_start: Start of content block
        - content_block_delta: Content delta
        - content_block_stop: End of content block
        - message_delta: Message metadata delta
        - message_stop: End of message
        """
        event_type = chunk.get("type")

        # Only process content_block_delta events
        if event_type == "content_block_delta":
            delta_data = chunk.get("delta", {})

            if delta_data.get("type") == "text_delta":
                content = delta_data.get("text", "")

                delta = MessageDelta(content=content)
                choice = StreamChoiceDelta(index=0, delta=delta)

                return StreamChunk(
                    id=chunk.get("message", {}).get("id", ""),
                    model=chunk.get("message", {}).get("model", ""),
                    choices=[choice],
                    created=int(time.time()),
                    provider="anthropic",
                )

        # Handle message_delta for finish reason
        elif event_type == "message_delta":
            delta_data = chunk.get("delta", {})
            finish_reason = delta_data.get("stop_reason")

            if finish_reason:
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
                provider="anthropic",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

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
                provider="anthropic",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

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
                            chunk = self._convert_stream_chunk(chunk_data)
                            if chunk:
                                yield chunk
                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider="anthropic",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

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
                            chunk = self._convert_stream_chunk(chunk_data)
                            if chunk:
                                yield chunk
                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider="anthropic",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise
