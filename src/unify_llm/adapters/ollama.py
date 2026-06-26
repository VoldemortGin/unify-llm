"""本地 Ollama provider(adapters 层):直连本机 /api/chat,无需 API key。

Ollama 在本地起服务(默认 http://localhost:11434),请求体用 ``messages`` + ``options``
(temperature/top_p/stop/num_predict),响应里 ``done`` 标记是否收尾;流式为换行分隔的
JSON 对象(newline-delimited JSON),每行 ``json.loads`` 后转换,``done`` 为真即停。

本文件是 OLD ``unify_llm.providers.ollama`` 在严格门禁下的现代化移植:parse-don't-validate
(私有 ``_Raw*`` pydantic 契约)、PEP604/内建泛型、``@override``、三分支错误归一(本地常见
ConnectError 经 ``self._network_error`` 落到 ProviderError)。
"""

import json
import time
from collections.abc import AsyncIterator, Iterator
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
    Role,
    StreamChoiceDelta,
    StreamChunk,
    Usage,
)


# ── parse-don't-validate:Ollama /api/chat 响应/流式 chunk 的最小 pydantic 契约 ──
class _RawMessage(BaseModel):
    """响应/chunk 里的 message 对象(只取 role + content)。"""

    role: Role = Role.ASSISTANT
    content: str = ""


class _RawResponse(BaseModel):
    """非流式 /api/chat 响应的最小契约。"""

    model: str = ""
    message: _RawMessage = Field(default_factory=_RawMessage)
    done: bool = False
    prompt_eval_count: int = 0
    eval_count: int = 0
    created_at: str | None = None


class _RawChunk(BaseModel):
    """流式换行分隔 JSON 单个 chunk 的最小契约。"""

    model: str = ""
    message: _RawMessage = Field(default_factory=_RawMessage)
    done: bool = False
    created_at: str | None = None


class OllamaProvider(BaseProvider):
    """Ollama provider implementation for local models.

    Ollama runs locally and exposes ``/api/chat`` for various models (Llama,
    Mistral, Phi, ...). No API key is required — headers are just Content-Type
    plus any configured extra headers.
    """

    @override
    def _get_headers(self) -> dict[str, str]:
        """Get headers for Ollama API requests (no auth, only Content-Type + extras)."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        headers.update(self.config.extra_headers)
        return headers

    @override
    def _get_base_url(self) -> str:
        """Get the base URL for Ollama API (defaults to the local daemon)."""
        return self.config.base_url or "http://localhost:11434"

    @override
    def _convert_request(self, request: ChatRequest) -> dict[str, object]:
        """Convert ChatRequest to Ollama API format.

        Ollama uses a format similar to OpenAI but funnels generation params
        through an ``options`` dict (``num_predict`` for max_tokens, ``stop`` as
        a list).
        """
        payload: dict[str, object] = {
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
        options: dict[str, object] = {}

        if request.temperature is not None:
            options["temperature"] = request.temperature

        if request.top_p is not None:
            options["top_p"] = request.top_p

        if request.stop is not None:
            options["stop"] = [request.stop] if isinstance(request.stop, str) else request.stop

        # Ollama uses num_predict instead of max_tokens
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens

        if options:
            payload["options"] = options

        # Add extra parameters
        payload.update(request.extra_params)

        return payload

    @override
    def _convert_response(self, response: dict[str, object]) -> ChatResponse:
        """Convert Ollama API response to ChatResponse (parse-don't-validate)."""
        parsed = _RawResponse.model_validate(response)

        message = Message(
            role=parsed.message.role,
            content=parsed.message.content,
        )

        choice = ChatResponseChoice(
            index=0,
            message=message,
            finish_reason=FinishReason.STOP if parsed.done else None,
        )

        # Ollama provides token counts in some responses
        usage = Usage(
            prompt_tokens=parsed.prompt_eval_count,
            completion_tokens=parsed.eval_count,
            total_tokens=parsed.prompt_eval_count + parsed.eval_count,
        )

        return ChatResponse(
            id=parsed.created_at if parsed.created_at is not None else str(int(time.time())),
            model=parsed.model,
            choices=[choice],
            usage=usage,
            created=int(time.time()),
            provider="ollama",
            raw_response=response,
        )

    @override
    def _convert_stream_chunk(self, chunk: dict[str, object]) -> StreamChunk | None:
        """Convert Ollama stream chunk to StreamChunk (parse-don't-validate)."""
        if not chunk:
            return None

        parsed = _RawChunk.model_validate(chunk)
        content = parsed.message.content

        # Skip empty content chunks unless it's the final chunk
        if not content and not parsed.done:
            return None

        delta = MessageDelta(content=content if content else None)

        choice = StreamChoiceDelta(
            index=0,
            delta=delta,
            finish_reason=FinishReason.STOP if parsed.done else None,
        )

        return StreamChunk(
            id=parsed.created_at if parsed.created_at is not None else str(int(time.time())),
            model=parsed.model,
            choices=[choice],
            created=int(time.time()),
            provider="ollama",
        )

    @override
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
        url = f"{self._get_base_url()}/api/chat"
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
                    except json.JSONDecodeError:
                        continue

                    parsed = _RawChunk.model_validate(chunk_data)
                    chunk = self._convert_stream_chunk(chunk_data)
                    if chunk:
                        yield chunk

                    # Stop if done
                    if parsed.done:
                        break

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
                    except json.JSONDecodeError:
                        continue

                    parsed = _RawChunk.model_validate(chunk_data)
                    chunk = self._convert_stream_chunk(chunk_data)
                    if chunk:
                        yield chunk

                    # Stop if done
                    if parsed.done:
                        break

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
