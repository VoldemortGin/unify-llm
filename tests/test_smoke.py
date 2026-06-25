"""冒烟:无 key、不连网,默认 MockProvider 跑通一次 chat 并返回合法 ChatResponse。

把"系统能不能跑"与"模型可不可用/要不要钱/网通不通"解耦。
"""

from unify_llm.adapters.mock import MockProvider
from unify_llm.models import ChatRequest, ChatResponse, Message


def test_mock_provider_chat_offline() -> None:
    provider = MockProvider()
    request = ChatRequest(model="mock-model", messages=[Message(role="user", content="ping")])
    response = provider.chat(request)
    assert isinstance(response, ChatResponse)
    assert response.choices
    assert response.content is not None
    assert response.provider == "mock"
