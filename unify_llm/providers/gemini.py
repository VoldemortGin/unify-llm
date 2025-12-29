"""Google Gemini provider implementation."""

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


class GeminiProvider(BaseProvider):
    """Google Gemini API provider implementation.

    Supports Gemini Pro, Gemini Pro Vision, and other Gemini models.
    """

    def _get_headers(self) -> dict:
        """Get headers for Gemini API requests."""
        headers = {
            "Content-Type": "application/json",
        }

        # Add any extra headers
        headers.update(self.config.extra_headers)

        return headers

    def _get_base_url(self) -> str:
        """Get the base URL for Gemini API."""
        return self.config.base_url or "https://generativelanguage.googleapis.com/v1beta"

    def _convert_request(self, request: ChatRequest) -> dict:
        """Convert ChatRequest to Gemini API format.

        Gemini API format:
        - Uses "contents" array with "parts" for each message
        - Role can be "user" or "model" (not "assistant")
        - System instructions are separate
        """
        # Separate system messages
        system_instruction = None
        contents = []

        for msg in request.messages:
            if msg.role == "system":
                # Gemini uses systemInstruction field
                if msg.content:
                    system_instruction = {"parts": [{"text": msg.content}]}
            else:
                # Map "assistant" to "model" for Gemini
                role = "model" if msg.role == "assistant" else msg.role

                contents.append({
                    "role": role,
                    "parts": [{"text": msg.content or ""}],
                })

        payload = {
            "contents": contents,
        }

        # Add system instruction if present
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        # Generation config
        generation_config = {}

        if request.temperature is not None:
            generation_config["temperature"] = request.temperature

        if request.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_tokens

        if request.top_p is not None:
            generation_config["topP"] = request.top_p

        if request.stop is not None:
            stop_sequences = (
                [request.stop] if isinstance(request.stop, str) else request.stop
            )
            generation_config["stopSequences"] = stop_sequences

        if generation_config:
            payload["generationConfig"] = generation_config

        # Add extra parameters
        payload.update(request.extra_params)

        return payload

    def _convert_response(self, response: dict) -> ChatResponse:
        """Convert Gemini API response to ChatResponse."""
        candidates = response.get("candidates", [])

        choices = []
        for i, candidate in enumerate(candidates):
            content_parts = candidate.get("content", {}).get("parts", [])
            content = ""

            # Combine all text parts
            for part in content_parts:
                if "text" in part:
                    content += part["text"]

            message = Message(
                role="assistant",
                content=content,
            )

            # Map Gemini finish reasons
            finish_reason_map = {
                "STOP": "stop",
                "MAX_TOKENS": "length",
                "SAFETY": "content_filter",
                "RECITATION": "content_filter",
            }
            gemini_reason = candidate.get("finishReason", "")
            finish_reason = finish_reason_map.get(gemini_reason, gemini_reason.lower())

            choices.append(
                ChatResponseChoice(
                    index=i,
                    message=message,
                    finish_reason=finish_reason if finish_reason else None,
                )
            )

        # Extract usage information
        usage_metadata = response.get("usageMetadata", {})
        usage = Usage(
            prompt_tokens=usage_metadata.get("promptTokenCount", 0),
            completion_tokens=usage_metadata.get("candidatesTokenCount", 0),
            total_tokens=usage_metadata.get("totalTokenCount", 0),
        )

        return ChatResponse(
            id=response.get("modelVersion", ""),
            model=response.get("modelVersion", ""),
            choices=choices,
            usage=usage,
            created=int(time.time()),
            provider="gemini",
            raw_response=response,
        )

    def _convert_stream_chunk(self, chunk: dict) -> Optional[StreamChunk]:
        """Convert Gemini stream chunk to StreamChunk."""
        if not chunk:
            return None

        candidates = chunk.get("candidates", [])
        if not candidates:
            return None

        choices = []
        for i, candidate in enumerate(candidates):
            content_parts = candidate.get("content", {}).get("parts", [])
            content = ""

            # Combine all text parts
            for part in content_parts:
                if "text" in part:
                    content += part["text"]

            delta = MessageDelta(content=content if content else None)

            # Map finish reason
            finish_reason_map = {
                "STOP": "stop",
                "MAX_TOKENS": "length",
                "SAFETY": "content_filter",
                "RECITATION": "content_filter",
            }
            gemini_reason = candidate.get("finishReason", "")
            finish_reason = finish_reason_map.get(gemini_reason, gemini_reason.lower())

            choices.append(
                StreamChoiceDelta(
                    index=i,
                    delta=delta,
                    finish_reason=finish_reason if finish_reason else None,
                )
            )

        if not choices:
            return None

        return StreamChunk(
            id=chunk.get("modelVersion", ""),
            model=chunk.get("modelVersion", ""),
            choices=choices,
            created=int(time.time()),
            provider="gemini",
        )

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
                provider="gemini",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

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
                provider="gemini",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

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
                        chunk = self._convert_stream_chunk(chunk_data)
                        if chunk:
                            yield chunk
                    except json.JSONDecodeError:
                        continue

        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider="gemini",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

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
                        chunk = self._convert_stream_chunk(chunk_data)
                        if chunk:
                            yield chunk
                    except json.JSONDecodeError:
                        continue

        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider="gemini",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise
