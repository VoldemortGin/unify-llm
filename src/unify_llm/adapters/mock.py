"""确定性离线默认实现(default,不是测试桩):无 key、不连网即可跑通主链路,同输入同输出。"""

from unify_llm.models import (
    ChatRequest,
    ChatResponse,
    ChatResponseChoice,
    Message,
    Usage,
)
from unify_llm.ports.llm import LLMProvider


class MockProvider:
    """确定性 mock LLM provider:回声式回复,created 固定以保证可复现。"""

    provider_name: str = "mock"

    def chat(self, request: ChatRequest, /) -> ChatResponse:
        last = request.messages[-1].content or ""
        reply = f"[mock:{request.model}] {last[:64]}"
        return ChatResponse(
            id="mock-0",
            model=request.model,
            choices=[
                ChatResponseChoice(
                    index=0,
                    message=Message(role="assistant", content=reply),
                    finish_reason="stop",
                )
            ],
            usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            created=0,
            provider=self.provider_name,
        )


# 结构化类型自检:确认 MockProvider 满足 Protocol(mypy 结构子类型 + beartype 双重确认)
_p: LLMProvider = MockProvider()
