"""Basic tests for UnifyLLM."""

import pytest
from unify_llm import UnifyLLM
from unify_llm.models import Message, ChatRequest
from unify_llm.exceptions import InvalidRequestError


def test_client_initialization():
    """Test client initialization with different providers."""
    # Should work with valid provider
    client = UnifyLLM(provider="openai", api_key="test-key")
    assert client is not None

    # Should raise error with invalid provider
    with pytest.raises(InvalidRequestError):
        UnifyLLM(provider="invalid_provider")


def test_message_creation():
    """Test Message model creation."""
    msg = Message(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"

    # System message
    sys_msg = Message(role="system", content="You are helpful")
    assert sys_msg.role == "system"


def test_message_validation():
    """Test Message validation."""
    # Empty content for non-tool messages should raise error
    with pytest.raises(ValueError):
        Message(role="user", content="")


def test_chat_request_creation():
    """Test ChatRequest model creation."""
    messages = [
        Message(role="user", content="Hello"),
    ]

    request = ChatRequest(
        model="gpt-4",
        messages=messages,
        temperature=0.7,
        max_tokens=100
    )

    assert request.model == "gpt-4"
    assert len(request.messages) == 1
    assert request.temperature == 0.7
    assert request.max_tokens == 100


def test_chat_request_validation():
    """Test ChatRequest validation."""
    # Empty messages should raise error
    with pytest.raises(ValueError):
        ChatRequest(model="gpt-4", messages=[])

    # Invalid temperature should raise error
    with pytest.raises(ValueError):
        ChatRequest(
            model="gpt-4",
            messages=[Message(role="user", content="test")],
            temperature=3.0  # > 2.0
        )


def test_provider_registration():
    """Test custom provider registration."""
    from unify_llm.providers import BaseProvider

    class CustomProvider(BaseProvider):
        def _get_headers(self):
            return {}

        def _get_base_url(self):
            return "http://test"

        def _convert_request(self, request):
            return {}

        def _convert_response(self, response):
            pass

        def _convert_stream_chunk(self, chunk):
            pass

        def _chat_impl(self, request):
            pass

        async def _achat_impl(self, request):
            pass

        def _chat_stream_impl(self, request):
            pass

        async def _achat_stream_impl(self, request):
            pass

    # Register custom provider
    UnifyLLM.register_provider("custom", CustomProvider)

    # Should be able to create client with custom provider
    client = UnifyLLM(provider="custom")
    assert client is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
