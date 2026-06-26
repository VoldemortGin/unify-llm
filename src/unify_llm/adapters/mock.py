"""确定性离线默认实现(default,不是测试桩):无 key、不连网即可跑通主链路,同输入同输出。

实现完整的 LLMProvider Protocol(chat / achat / chat_stream / achat_stream),回声式回复,
created 固定为 0 以保证可复现。生产缺 key 时工厂会硬失败(绝不静默回退到本类);非生产/CI/离线
才以本类兜底。
"""

from collections.abc import AsyncIterator, Iterator

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
from unify_llm.ports.llm import LLMProvider


class MockProvider:
    """确定性 mock LLM provider:回声式回复,流式按词切块,全程无 I/O。"""

    provider_name: str = "mock"

    def _reply(self, request: ChatRequest) -> str:
        last = request.messages[-1].content if request.messages else None
        return f"[mock:{request.model}] {(last or '')[:64]}"

    def _response(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            id="mock-0",
            model=request.model,
            choices=[
                ChatResponseChoice(
                    index=0,
                    message=Message(role=Role.ASSISTANT, content=self._reply(request)),
                    finish_reason=FinishReason.STOP,
                )
            ],
            usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            created=0,
            provider=self.provider_name,
        )

    def _chunks(self, request: ChatRequest) -> list[StreamChunk]:
        reply = self._reply(request)
        # 按空白切词,逐词成块;末块带 finish_reason=stop。
        words = reply.split(" ") or [reply]
        chunks: list[StreamChunk] = []
        for i, word in enumerate(words):
            piece = word if i == 0 else f" {word}"
            is_last = i == len(words) - 1
            chunks.append(
                StreamChunk(
                    id="mock-0",
                    model=request.model,
                    choices=[
                        StreamChoiceDelta(
                            index=0,
                            delta=MessageDelta(
                                role=Role.ASSISTANT if i == 0 else None,
                                content=piece,
                            ),
                            finish_reason=FinishReason.STOP if is_last else None,
                        )
                    ],
                    created=0,
                    provider=self.provider_name,
                )
            )
        return chunks

    def chat(self, request: ChatRequest, /) -> ChatResponse:
        return self._response(request)

    async def achat(self, request: ChatRequest, /) -> ChatResponse:
        return self._response(request)

    def chat_stream(self, request: ChatRequest, /) -> Iterator[StreamChunk]:
        yield from self._chunks(request)

    async def achat_stream(self, request: ChatRequest, /) -> AsyncIterator[StreamChunk]:
        for chunk in self._chunks(request):
            yield chunk


# 结构化类型自检:确认 MockProvider 满足 Protocol(mypy 结构子类型 + beartype 双重确认)
_p: LLMProvider = MockProvider()
