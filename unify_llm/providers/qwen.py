"""Qwen (通义千问) provider implementation."""

import json
import time
from typing import AsyncIterator, Iterator, Optional

import httpx
import rootutils

ROOT_DIR = rootutils.setup_root(search_from=__file__, indicator=[".project-root"], pythonpath=True)

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
from unify_llm.exceptions import TimeoutError as UnifyTimeoutError


class QwenProvider(BaseProvider):
    """Qwen (Alibaba Cloud) API provider implementation.

    Supports Qwen-Max, Qwen-Plus, Qwen-Turbo and other Qwen models.
    API endpoint: https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
    """

    def _get_headers(self) -> dict:
        """Get headers for Qwen API requests."""
        headers = {
            "Content-Type": "application/json",
        }

        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        headers.update(self.config.extra_headers)
        return headers

    def _get_base_url(self) -> str:
        """Get the base URL for Qwen API."""
        return self.config.base_url or "https://dashscope.aliyuncs.com/api/v1"

    def _convert_request(self, request: ChatRequest) -> dict:
        """Convert ChatRequest to Qwen API format."""
        # Separate system messages from conversation messages
        system_content = None
        messages = []

        for msg in request.messages:
            if msg.role == "system":
                # Qwen combines multiple system messages
                if system_content:
                    system_content += "\n" + (msg.content or "")
                else:
                    system_content = msg.content
            else:
                messages.append({
                    "role": msg.role,
                    "content": msg.content or "",
                })

        payload = {
            "model": request.model,
            "input": {
                "messages": messages,
            },
        }

        # Add system message if present
        if system_content:
            payload["input"]["messages"].insert(0, {
                "role": "system",
                "content": system_content,
            })

        # Build parameters object
        parameters = {}

        if request.temperature is not None:
            parameters["temperature"] = request.temperature

        if request.max_tokens is not None:
            parameters["max_tokens"] = request.max_tokens

        if request.top_p is not None:
            parameters["top_p"] = request.top_p

        if request.stop is not None:
            parameters["stop"] = request.stop

        # Qwen uses "incremental_output" for streaming
        if request.stream:
            parameters["incremental_output"] = True

        if parameters:
            payload["parameters"] = parameters

        # Add extra parameters
        if request.extra_params:
            if "parameters" not in payload:
                payload["parameters"] = {}
            payload["parameters"].update(request.extra_params)

        return payload

    def _convert_response(self, response: dict) -> ChatResponse:
        """Convert Qwen API response to ChatResponse."""
        output = response.get("output", {})
        usage_data = response.get("usage", {})

        # Extract message content
        choices = output.get("choices", [])
        converted_choices = []

        for idx, choice in enumerate(choices):
            message_data = choice.get("message", {})
            message = Message(
                role=message_data.get("role", "assistant"),
                content=message_data.get("content"),
            )
            converted_choices.append(
                ChatResponseChoice(
                    index=idx,
                    message=message,
                    finish_reason=choice.get("finish_reason"),
                )
            )

        # If no choices, try to get text directly from output
        if not converted_choices and output.get("text"):
            message = Message(
                role="assistant",
                content=output.get("text"),
            )
            converted_choices.append(
                ChatResponseChoice(
                    index=0,
                    message=message,
                    finish_reason=output.get("finish_reason", "stop"),
                )
            )

        usage = Usage(
            prompt_tokens=usage_data.get("input_tokens", 0),
            completion_tokens=usage_data.get("output_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        return ChatResponse(
            id=response.get("request_id", ""),
            model=request.model if hasattr(request, 'model') else "",
            choices=converted_choices,
            usage=usage,
            created=int(time.time()),
            provider="qwen",
            raw_response=response,
        )

    def _convert_stream_chunk(self, chunk: dict) -> Optional[StreamChunk]:
        """Convert Qwen stream chunk to StreamChunk."""
        if not chunk:
            return None

        output = chunk.get("output", {})

        # Get content from output
        content = output.get("text")
        finish_reason = output.get("finish_reason")

        choices = output.get("choices", [])
        converted_choices = []

        if choices:
            for idx, choice in enumerate(choices):
                message_data = choice.get("message", {})
                delta = MessageDelta(
                    role=message_data.get("role"),
                    content=message_data.get("content"),
                )
                converted_choices.append(
                    StreamChoiceDelta(
                        index=idx,
                        delta=delta,
                        finish_reason=choice.get("finish_reason"),
                    )
                )
        elif content:
            # Fallback to text field
            delta = MessageDelta(
                role="assistant",
                content=content,
            )
            converted_choices.append(
                StreamChoiceDelta(
                    index=0,
                    delta=delta,
                    finish_reason=finish_reason,
                )
            )

        if not converted_choices:
            return None

        return StreamChunk(
            id=chunk.get("request_id", ""),
            model="",
            choices=converted_choices,
            created=int(time.time()),
            provider="qwen",
        )

    def _chat_impl(self, request: ChatRequest) -> ChatResponse:
        """Implementation of synchronous chat request."""
        url = f"{self._get_base_url()}/services/aigc/text-generation/generation"
        payload = self._convert_request(request)

        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            return self._convert_response(response.json())
        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider="qwen",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

    async def _achat_impl(self, request: ChatRequest) -> ChatResponse:
        """Implementation of asynchronous chat request."""
        url = f"{self._get_base_url()}/services/aigc/text-generation/generation"
        payload = self._convert_request(request)

        try:
            response = await self.async_client.post(url, json=payload)
            response.raise_for_status()
            return self._convert_response(response.json())
        except httpx.TimeoutException as e:
            raise UnifyTimeoutError(
                message=f"Request timed out after {self.config.timeout}s",
                provider="qwen",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

    def _chat_stream_impl(self, request: ChatRequest) -> Iterator[StreamChunk]:
        """Implementation of synchronous streaming chat request."""
        url = f"{self._get_base_url()}/services/aigc/text-generation/generation"
        payload = self._convert_request(request)

        # Ensure streaming is enabled
        if "parameters" not in payload:
            payload["parameters"] = {}
        payload["parameters"]["incremental_output"] = True

        try:
            with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line.strip():
                        continue

                    # Qwen uses SSE format with "data:" prefix
                    if line.startswith("data:"):
                        data = line[5:].strip()  # Remove "data:" prefix

                        if not data or data == "[DONE]":
                            break

                        try:
                            chunk_data = json.loads(data)
                            chunk = self._convert_stream_chunk(chunk_data)
                            if chunk:
                                yield chunk
                        except json.JSONDecodeError:
                            continue
                    else:
                        # Some responses might not have data: prefix
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
                provider="qwen",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise

    async def _achat_stream_impl(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """Implementation of asynchronous streaming chat request."""
        url = f"{self._get_base_url()}/services/aigc/text-generation/generation"
        payload = self._convert_request(request)

        # Ensure streaming is enabled
        if "parameters" not in payload:
            payload["parameters"] = {}
        payload["parameters"]["incremental_output"] = True

        try:
            async with self.async_client.stream("POST", url, json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    # Qwen uses SSE format with "data:" prefix
                    if line.startswith("data:"):
                        data = line[5:].strip()  # Remove "data:" prefix

                        if not data or data == "[DONE]":
                            break

                        try:
                            chunk_data = json.loads(data)
                            chunk = self._convert_stream_chunk(chunk_data)
                            if chunk:
                                yield chunk
                        except json.JSONDecodeError:
                            continue
                    else:
                        # Some responses might not have data: prefix
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
                provider="qwen",
            ) from e
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise
