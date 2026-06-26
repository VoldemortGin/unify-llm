"""阿里云通义千问 / DashScope provider(adapters 层)。

DashScope 文本生成接口形状与 OpenAI 不同:请求体为 ``input.messages`` + ``parameters``,
多条 system 消息合并成单条置顶 system;流式靠 ``parameters.incremental_output=True`` 开启,
响应落在 ``output`` 下(优先 ``output.choices[].message``,否则回退 ``output.text``),用量为
``{input_tokens, output_tokens, total_tokens}``,顶层带 ``request_id``;SSE 既有 ``data:`` 前缀
行也有无前缀整行回退;端点 ``/services/aigc/text-generation/generation``。

本文件是 OLD ``unify_llm.providers.qwen`` 在严格门禁下的现代化移植:parse-don't-validate
(私有 ``_Raw*`` pydantic 契约)、PEP604/内建泛型、``@override``、``to_finish_reason`` 归一
DashScope 的 ``"null"`` 等非枚举原因,以及三分支错误归一(超时优先、状态码、网络错兜底)。
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
    Message,
    MessageDelta,
    Role,
    StreamChoiceDelta,
    StreamChunk,
    Usage,
)


# ── parse-don't-validate:DashScope text-generation 响应/流式 chunk 的最小契约 ──
class _RawMessage(BaseModel):
    """``output.choices[].message`` 对象(role 缺省时为 None,由转换层按上下文补默认)。"""

    role: Role | None = None
    content: str | None = None


class _RawChoice(BaseModel):
    """``output.choices`` 的单个 choice;``finish_reason`` 保留原始串待 to_finish_reason 归一。"""

    message: _RawMessage = Field(default_factory=_RawMessage)
    finish_reason: str | None = None


class _RawOutput(BaseModel):
    """``output`` 节点:既建模 ``choices`` 主路径,也建模 ``text`` 回退路径。"""

    choices: list[_RawChoice] = Field(default_factory=list)
    text: str | None = None
    finish_reason: str | None = None


class _RawUsage(BaseModel):
    """``usage`` 计数(DashScope 命名:input/output/total tokens)。"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class _RawResponse(BaseModel):
    """非流式响应的最小契约。"""

    output: _RawOutput = Field(default_factory=_RawOutput)
    usage: _RawUsage = Field(default_factory=_RawUsage)
    request_id: str = ""
    model: str = ""


class _RawChunk(BaseModel):
    """流式 chunk 的最小契约(复用同一 ``output``-形状模型)。"""

    output: _RawOutput = Field(default_factory=_RawOutput)
    request_id: str = ""


class QwenProvider(BaseProvider):
    """Qwen (Alibaba Cloud) API provider implementation.

    Supports Qwen-Max, Qwen-Plus, Qwen-Turbo and other Qwen models.
    API endpoint: https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
    """

    @override
    def _get_headers(self) -> dict[str, str]:
        """Get headers for Qwen API requests (Bearer auth + configured extras)."""
        headers: dict[str, str] = {"Content-Type": "application/json"}

        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        headers.update(self.config.extra_headers)
        return headers

    @override
    def _get_base_url(self) -> str:
        """Get the base URL for Qwen API."""
        return self.config.base_url or "https://dashscope.aliyuncs.com/api/v1"

    @override
    def _convert_request(self, request: ChatRequest) -> dict[str, object]:
        """Convert ChatRequest to Qwen (DashScope) API format.

        System messages are merged into a single leading system message;
        generation params funnel through ``parameters`` (with extra_params
        merged in), and ``incremental_output`` is enabled for streaming.
        """
        # Separate system messages from conversation messages
        system_content: str | None = None
        messages: list[dict[str, object]] = []

        for msg in request.messages:
            if msg.role == Role.SYSTEM:
                # Qwen combines multiple system messages
                if system_content:
                    system_content += "\n" + (msg.content or "")
                else:
                    system_content = msg.content
            else:
                messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content or "",
                    }
                )

        # Add system message if present
        if system_content:
            messages.insert(
                0,
                {
                    "role": "system",
                    "content": system_content,
                },
            )

        payload: dict[str, object] = {
            "model": request.model,
            "input": {
                "messages": messages,
            },
        }

        # Build parameters object
        parameters: dict[str, object] = {}

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

        # Merge extra parameters into the parameters object
        parameters.update(request.extra_params)

        if parameters:
            payload["parameters"] = parameters

        return payload

    @override
    def _convert_response(self, response: dict[str, object]) -> ChatResponse:
        """Convert Qwen API response to ChatResponse (parse-don't-validate)."""
        parsed = _RawResponse.model_validate(response)
        output = parsed.output

        # Extract message content from choices
        converted_choices: list[ChatResponseChoice] = []

        for idx, choice in enumerate(output.choices):
            message = Message(
                role=choice.message.role or Role.ASSISTANT,
                content=choice.message.content,
            )
            converted_choices.append(
                ChatResponseChoice(
                    index=idx,
                    message=message,
                    finish_reason=to_finish_reason(choice.finish_reason),
                )
            )

        # If no choices, try to get text directly from output
        if not converted_choices and output.text:
            message = Message(
                role=Role.ASSISTANT,
                content=output.text,
            )
            converted_choices.append(
                ChatResponseChoice(
                    index=0,
                    message=message,
                    finish_reason=to_finish_reason(output.finish_reason or "stop"),
                )
            )

        usage = Usage(
            prompt_tokens=parsed.usage.input_tokens,
            completion_tokens=parsed.usage.output_tokens,
            total_tokens=parsed.usage.total_tokens,
        )

        return ChatResponse(
            id=parsed.request_id,
            model=parsed.model,
            choices=converted_choices,
            usage=usage,
            created=int(time.time()),
            provider="qwen",
            raw_response=response,
        )

    @override
    def _convert_stream_chunk(self, chunk: dict[str, object]) -> StreamChunk | None:
        """Convert Qwen stream chunk to StreamChunk (parse-don't-validate)."""
        if not chunk:
            return None

        parsed = _RawChunk.model_validate(chunk)
        output = parsed.output

        converted_choices: list[StreamChoiceDelta] = []

        if output.choices:
            for idx, choice in enumerate(output.choices):
                delta = MessageDelta(
                    role=choice.message.role,
                    content=choice.message.content,
                )
                converted_choices.append(
                    StreamChoiceDelta(
                        index=idx,
                        delta=delta,
                        finish_reason=to_finish_reason(choice.finish_reason),
                    )
                )
        elif output.text:
            # Fallback to text field
            delta = MessageDelta(
                role=Role.ASSISTANT,
                content=output.text,
            )
            converted_choices.append(
                StreamChoiceDelta(
                    index=0,
                    delta=delta,
                    finish_reason=to_finish_reason(output.finish_reason),
                )
            )

        if not converted_choices:
            return None

        return StreamChunk(
            id=parsed.request_id,
            model="",
            choices=converted_choices,
            created=int(time.time()),
            provider="qwen",
        )

    @override
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
        url = f"{self._get_base_url()}/services/aigc/text-generation/generation"
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
        url = f"{self._get_base_url()}/services/aigc/text-generation/generation"
        payload = self._convert_request(request)

        # Ensure streaming is enabled
        params = payload.get("parameters")
        if isinstance(params, dict):
            params["incremental_output"] = True
        else:
            payload["parameters"] = {"incremental_output": True}

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
                        except json.JSONDecodeError:
                            continue
                    else:
                        # Some responses might not have data: prefix
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
        url = f"{self._get_base_url()}/services/aigc/text-generation/generation"
        payload = self._convert_request(request)

        # Ensure streaming is enabled
        params = payload.get("parameters")
        if isinstance(params, dict):
            params["incremental_output"] = True
        else:
            payload["parameters"] = {"incremental_output": True}

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
                        except json.JSONDecodeError:
                            continue
                    else:
                        # Some responses might not have data: prefix
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
