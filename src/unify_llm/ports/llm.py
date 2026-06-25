"""模型无关缝(最小骨架):LLM provider 的 Protocol 契约;完整缝(多方法 + factory)留 Phase 3。

以 unify_llm.models 的 ChatRequest / ChatResponse 为边界契约。核心/领域代码只依赖本
Protocol,绝不 import 厂商 SDK——"换模型"从重构降级为加一个 adapter 类。
"""

from typing import Protocol, runtime_checkable

from unify_llm.models import ChatRequest, ChatResponse


@runtime_checkable
class LLMProvider(Protocol):
    """统一的同步对话契约。"""

    def chat(self, request: ChatRequest, /) -> ChatResponse: ...
