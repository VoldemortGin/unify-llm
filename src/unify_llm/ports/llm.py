"""模型无关缝(完整 Protocol 契约,ADR-05):LLM provider 的 4 法对话接口。

以 unify_llm.models 的 ChatRequest / ChatResponse / StreamChunk 为边界契约。核心/领域代码
只依赖本 Protocol,绝不 import 厂商 SDK——"换模型"从重构降级为加一个 adapter 类。

`@runtime_checkable` 让 ``isinstance(impl, LLMProvider)`` 在运行时按"方法是否齐全"结构判定
(Sendable 之类的语言级标记不适用于 Python)。
"""

from collections.abc import AsyncIterator, Iterator
from typing import Protocol, runtime_checkable

from unify_llm.models import ChatRequest, ChatResponse, StreamChunk


@runtime_checkable
class LLMProvider(Protocol):
    """统一的同步/异步 + 非流式/流式对话契约(签名对齐 BaseProvider 的公开方法)。"""

    def chat(self, request: ChatRequest, /) -> ChatResponse:
        """同步非流式对话:返回一个完整 ChatResponse。"""
        ...

    async def achat(self, request: ChatRequest, /) -> ChatResponse:
        """异步非流式对话:返回一个完整 ChatResponse。"""
        ...

    def chat_stream(self, request: ChatRequest, /) -> Iterator[StreamChunk]:
        """同步流式对话:逐块产出 StreamChunk。"""
        ...

    def achat_stream(self, request: ChatRequest, /) -> AsyncIterator[StreamChunk]:
        """异步流式对话:逐块产出 StreamChunk(实现为 async generator)。"""
        ...
