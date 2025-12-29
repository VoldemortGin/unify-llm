"""Ollama provider implementation for local models."""

import json
import time
from typing import AsyncIterator, Iterator, Optional

import httpx

from unify_llm.models import (
    ChatRequest,
    ChatResponse,
    ChatResponseChoice,
    Message,
    MessageDelta,
    ProviderConfig,
    StreamChunk,
    StreamChoiceDelta,
    Usage,
)
from unify_llm.providers.base import BaseProvider
from unify_llm.exceptions import TimeoutError as UnifyTimeoutError


class OllamaProvider(BaseProvider):
    """Ollama provider implementation for local models.

    Ollama runs locally and provides OpenAI-compatible API for various models
    including Llama, Mistral, Phi, and others.
    """

    def _get_headers(self) -> dict:
        """Get headers for Ollama API requests."""
        headers = {
            "Content-Type": "application/json",
        }

        # Add any extra headers
        headers.update(self.config.extra_headers)

        return headers

    def _get_base_url(self) -> str:
        """Get the base URL for Ollama API."""
        return self.config.base_url or "http://localhost:11434"

    def _convert_request(self, request: ChatRequest) -> dict:
        """Convert ChatRequest to Ollama API format.

        Ollama uses a format similar to OpenAI but with some differences.
        """
        payload = {
            "model": request.model,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content or "",
                }
                for msg in request.messages
            ],
            "stream": request.stream,
        }

        # Ollama uses "options" for generation parameters
        options = {}

        if request.temperature is not None:
            options["temperature"] = request.temperature

        if request.top_p is not None:
            options["top_p"] = request.top_p

        if request.stop is not None:
            options["stop"] = (
                [request.stop] if isinstance(request.stop, str) else request.stop
            )

        # Ollama uses num_predict instead of max_tokens
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens

        if options:
            payload["options"] = options

        # Add extra parameters
        payload.update(request.extra_params)

        return payload

    def _convert_response(self, response: dict) -> ChatResponse:
        """Convert Ollama API response to ChatResponse."""
        message_data = response.get("message", {})
        message = Message(
            role=message_data.get("role", "assistant"),
            content=message_data.get("content", ""),
        )

        choice = ChatResponseChoice(
            index=0,
            message=message,
            finish_reason="stop" if response.get("done") else None,
        )

        # Ollama provides token counts in some responses
        usage = Usage(
            prompt_tokens=response.get("prompt_eval_count", 0),
            completion_tokens=response.get("eval_count", 0),
            total_tokens=(
                response.get("prompt_eval_count", 0) + response.get("eval_count", 0)
            ),
        )

        return ChatResponse(
            id=response.get("created_at", str(int(time.time()))),
            model=response.get("model", ""),
            choices=[choice],
            usage=usage,
            created=int(time.time()),
            provider="ollama",
            raw_response=response,
        )

    def _convert_stream_chunk(self, chunk: dict) -> Optional[StreamChunk]:
        """Convert Ollama stream chunk to StreamChunk."""
        if not chunk:
            return None

        message_data = chunk.get("message", {})
        content = message_data.get("content", "")

        # Skip empty content chunks unless it's the final chunk
        if not content and not chunk.get("done"):
            return None

        delta = MessageDelta(content=content if content else None)

        choice = StreamChoiceDelta(
            index=0,
            delta=delta,
            finish_reason="stop" if chunk.get("done") else None,
        )

        return StreamChunk(
            id=chunk.get("created_at", str(int(time.time()))),
            model=chunk.get("model", ""),
            choices=[choice],
            created=int(time.time()),
            provider="ollama",
        )

    def _chat_impl(self, request: ChatRequest) -> ChatResponse:
        """Implementation of synchronous chat request."""
        url = f"{self._get_base_url()}/api/chat"
        payload = self._convert_request(request)

        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            return self._convert_response(response.json())
        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider="ollama",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

    async def _achat_impl(self, request: ChatRequest) -> ChatResponse:
        """Implementation of asynchronous chat request."""
        url = f"{self._get_base_url()}/api/chat"
        payload = self._convert_request(request)

        try:
            response = await self.async_client.post(url, json=payload)
            response.raise_for_status()
            return self._convert_response(response.json())
        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider="ollama",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

    def _chat_stream_impl(self, request: ChatRequest) -> Iterator[StreamChunk]:
        """Implementation of synchronous streaming chat request."""
        url = f"{self._get_base_url()}/api/chat"
        payload = self._convert_request(request)

        try:
            with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()

                # Ollama streams newline-delimited JSON objects
                for line in response.iter_lines():
                    if not line.strip():
                        continue

                    try:
                        chunk_data = json.loads(line)
                        chunk = self._convert_stream_chunk(chunk_data)
                        if chunk:
                            yield chunk

                        # Stop if done
                        if chunk_data.get("done"):
                            break

                    except json.JSONDecodeError:
                        continue

        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider="ollama",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

    async def _achat_stream_impl(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """Implementation of asynchronous streaming chat request."""
        url = f"{self._get_base_url()}/api/chat"
        payload = self._convert_request(request)

        try:
            async with self.async_client.stream("POST", url, json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    try:
                        chunk_data = json.loads(line)
                        chunk = self._convert_stream_chunk(chunk_data)
                        if chunk:
                            yield chunk

                        # Stop if done
                        if chunk_data.get("done"):
                            break

                    except json.JSONDecodeError:
                        continue

        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider="ollama",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise
