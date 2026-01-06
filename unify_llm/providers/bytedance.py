"""ByteDance (Doubao/豆包) provider implementation."""

import json
import time
from typing import AsyncIterator, Iterator, Optional

import httpx
import rootutils

ROOT_DIR = rootutils.setup_root(search_from=__file__, indicator=[".project-root"], pythonpath=True)

from unify_llm.exceptions import TimeoutError as UnifyTimeoutError
from unify_llm.models import (
    ChatRequest,
    ChatResponse,
    ChatResponseChoice,
    Message,
    MessageDelta,
    StreamChunk,
    StreamChoiceDelta,
    Usage,
)
from unify_llm.providers.base import BaseProvider


class ByteDanceProvider(BaseProvider):
    """ByteDance Doubao (豆包) API provider implementation.

    Supports Doubao models from ByteDance.
    API endpoint: https://ark.cn-beijing.volces.com/api/v3/chat/completions
    """

    def _get_headers(self) -> dict:
        """Get headers for ByteDance API requests."""
        headers = {
            "Content-Type": "application/json",
        }

        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        headers.update(self.config.extra_headers)
        return headers

    def _get_base_url(self) -> str:
        """Get the base URL for ByteDance API."""
        return self.config.base_url or "https://ark.cn-beijing.volces.com/api/v3"

    def _convert_request(self, request: ChatRequest) -> dict:
        """Convert ChatRequest to ByteDance API format.

        ByteDance API is compatible with OpenAI format.
        """
        payload = {
            "model": request.model,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content or "",
                    **({"name": msg.name} if msg.name else {}),
                }
                for msg in request.messages
            ],
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

        if request.stream:
            payload["stream"] = True

        # Add extra parameters
        payload.update(request.extra_params)

        return payload

    def _convert_response(self, response: dict) -> ChatResponse:
        """Convert ByteDance API response to ChatResponse."""
        choices = []
        for choice in response.get("choices", []):
            msg_data = choice.get("message", {})
            message = Message(
                role=msg_data.get("role", "assistant"),
                content=msg_data.get("content"),
            )
            choices.append(
                ChatResponseChoice(
                    index=choice.get("index", 0),
                    message=message,
                    finish_reason=choice.get("finish_reason"),
                )
            )

        usage_data = response.get("usage", {})
        usage = Usage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        return ChatResponse(
            id=response.get("id", ""),
            model=response.get("model", ""),
            choices=choices,
            usage=usage,
            created=response.get("created", int(time.time())),
            provider="bytedance",
            raw_response=response,
        )

    def _convert_stream_chunk(self, chunk: dict) -> Optional[StreamChunk]:
        """Convert ByteDance stream chunk to StreamChunk."""
        if not chunk:
            return None

        choices = []
        for choice in chunk.get("choices", []):
            delta_data = choice.get("delta", {})
            delta = MessageDelta(
                role=delta_data.get("role"),
                content=delta_data.get("content"),
            )
            choices.append(
                StreamChoiceDelta(
                    index=choice.get("index", 0),
                    delta=delta,
                    finish_reason=choice.get("finish_reason"),
                )
            )

        if not choices:
            return None

        return StreamChunk(
            id=chunk.get("id", ""),
            model=chunk.get("model", ""),
            choices=choices,
            created=chunk.get("created", int(time.time())),
            provider="bytedance",
        )

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
                provider="bytedance",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

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
                provider="bytedance",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

    def _chat_stream_impl(self, request: ChatRequest) -> Iterator[StreamChunk]:
        """Implementation of synchronous streaming chat request."""
        url = f"{self._get_base_url()}/chat/completions"
        payload = self._convert_request(request)
        payload["stream"] = True

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
                provider="bytedance",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

    async def _achat_stream_impl(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """Implementation of asynchronous streaming chat request."""
        url = f"{self._get_base_url()}/chat/completions"
        payload = self._convert_request(request)
        payload["stream"] = True

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
                provider="bytedance",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise
