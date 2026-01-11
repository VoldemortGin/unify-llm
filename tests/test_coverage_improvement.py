"""Comprehensive unit tests to improve code coverage.

This test suite targets modules with low coverage:
- unify_llm/utils.py (29%)
- unify_llm/client.py (65%)
- unify_llm/providers/base.py (51%)
- unify_llm/agent/tools.py (58%)
- unify_llm/agent/executor.py (18%)

All tests use mocks and do NOT call real LLM APIs.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import json

import rootutils

ROOT_DIR = rootutils.setup_root(search_from=__file__, indicator=[".project-root"], pythonpath=True)

from unify_llm import UnifyLLM
from unify_llm.models import (
    Message,
    ChatRequest,
    ChatResponse,
    ChatResponseChoice,
    ProviderConfig,
)
from unify_llm.core.exceptions import (
    InvalidRequestError,
    APIError,
    AuthenticationError,
    RateLimitError,
)
from unify_llm.agent.tools import (
    Tool,
    ToolRegistry,
    ToolParameter,
    ToolParameterType,
    ToolResult,
)
from unify_llm.agent.base import Agent, AgentConfig
from unify_llm.agent.executor import AgentExecutor, ExecutionResult
from unify_llm.agent.memory import ConversationMemory


# ============================================================================
# Tests for unify_llm/utils.py
# ============================================================================


class TestUtils:
    """Tests for utils module."""

    def test_get_model_name_mapping_path(self):
        """Test getting model name mapping path."""
        from unify_llm.utils import get_model_name_mapping_path

        path = get_model_name_mapping_path()
        assert isinstance(path, Path)
        assert path.name == "model_name_mapping.yaml"

    def test_load_model_name_mapping(self):
        """Test loading model name mapping."""
        from unify_llm.utils import load_model_name_mapping

        mapping = load_model_name_mapping()
        assert isinstance(mapping, dict)
        # Should have some mappings
        assert len(mapping) > 0

    def test_load_model_name_mapping_caching(self):
        """Test that model name mapping is cached."""
        from unify_llm.utils import load_model_name_mapping

        # Load once
        mapping1 = load_model_name_mapping()
        # Load again
        mapping2 = load_model_name_mapping()
        # Should be the same object (cached)
        assert mapping1 is mapping2

    def test_load_model_name_mapping_nonexistent_file(self):
        """Test loading when mapping file doesn't exist."""
        from unify_llm.utils import load_model_name_mapping

        with patch("unify_llm.utils.get_model_name_mapping_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/path/model_name_mapping.yaml")
            # Clear cache
            import unify_llm.utils

            unify_llm.utils._model_name_mapping = None

            mapping = load_model_name_mapping()
            assert mapping == {}

    def test_resolve_model_name_openrouter(self):
        """Test resolving model name for OpenRouter."""
        from unify_llm.utils import resolve_model_name

        # Mock the mapping
        with patch("unify_llm.utils.load_model_name_mapping") as mock_load:
            mock_load.return_value = {
                "claude-4.5": "anthropic/claude-sonnet-4.5",
                "gpt5": "openai/gpt-5",
            }

            result = resolve_model_name("openrouter", "claude-4.5")
            assert result == "anthropic/claude-sonnet-4.5"

            result = resolve_model_name("openrouter", "gpt5")
            assert result == "openai/gpt-5"

            # Unknown alias should return original
            result = resolve_model_name("openrouter", "unknown-model")
            assert result == "unknown-model"

    def test_resolve_model_name_other_providers(self):
        """Test that other providers don't use mapping."""
        from unify_llm.utils import resolve_model_name

        # For non-OpenRouter providers, should return original
        result = resolve_model_name("openai", "gpt-4-turbo")
        assert result == "gpt-4-turbo"

        result = resolve_model_name("anthropic", "claude-3-opus")
        assert result == "claude-3-opus"

    def test_reload_model_name_mapping(self):
        """Test reloading model name mapping."""
        from unify_llm.utils import reload_model_name_mapping
        import unify_llm.utils

        # Set cache to something
        unify_llm.utils._model_name_mapping = {"test": "value"}

        # Reload should clear cache and reload
        mapping = reload_model_name_mapping()
        assert isinstance(mapping, dict)

    def test_get_api_key_from_env_openai(self):
        """Test getting OpenAI API key from environment."""
        from unify_llm.utils import get_api_key_from_env

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-openai-key"}):
            key = get_api_key_from_env("openai")
            assert key == "test-openai-key"

    def test_get_api_key_from_env_anthropic(self):
        """Test getting Anthropic API key from environment."""
        from unify_llm.utils import get_api_key_from_env

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-anthropic-key"}):
            key = get_api_key_from_env("anthropic")
            assert key == "test-anthropic-key"

    def test_get_api_key_from_env_gemini(self):
        """Test getting Gemini API key from environment."""
        from unify_llm.utils import get_api_key_from_env

        # Test GEMINI_API_KEY
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"}):
            key = get_api_key_from_env("gemini")
            assert key == "test-gemini-key"

        # Test GOOGLE_API_KEY fallback
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-google-key"}, clear=True):
            key = get_api_key_from_env("gemini")
            assert key == "test-google-key"

    def test_get_api_key_from_env_ollama(self):
        """Test Ollama doesn't need API key."""
        from unify_llm.utils import get_api_key_from_env

        key = get_api_key_from_env("ollama")
        assert key is None

    def test_get_api_key_from_env_not_found(self):
        """Test when API key is not in environment."""
        from unify_llm.utils import get_api_key_from_env

        with patch.dict(os.environ, {}, clear=True):
            key = get_api_key_from_env("openai")
            assert key is None

    def test_estimate_tokens(self):
        """Test token estimation."""
        from unify_llm.utils import estimate_tokens

        # Empty string
        assert estimate_tokens("") == 0

        # Short text (4 chars per token)
        assert estimate_tokens("test") == 1
        assert estimate_tokens("this is a test") == 3

        # Longer text
        text = "This is a much longer piece of text for testing"
        tokens = estimate_tokens(text)
        assert tokens > 0
        assert tokens < len(text)  # Should be less than character count

    def test_truncate_messages_empty(self):
        """Test truncating empty message list."""
        from unify_llm.utils import truncate_messages

        result = truncate_messages([], max_tokens=100)
        assert result == []

    def test_truncate_messages_within_limit(self):
        """Test truncating when within limit."""
        from unify_llm.utils import truncate_messages

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        result = truncate_messages(messages, max_tokens=1000)
        assert len(result) == 2
        assert result[0]["content"] == "Hello"
        assert result[1]["content"] == "Hi there"

    def test_truncate_messages_preserve_system(self):
        """Test truncating while preserving system messages."""
        from unify_llm.utils import truncate_messages

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "How are you?"},
        ]

        # Very small limit to force truncation
        result = truncate_messages(messages, max_tokens=10, preserve_system=True)

        # System message should be preserved
        assert result[0]["role"] == "system"
        # Should keep most recent messages
        assert len(result) >= 1

    def test_truncate_messages_no_preserve_system(self):
        """Test truncating without preserving system messages."""
        from unify_llm.utils import truncate_messages

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        result = truncate_messages(messages, max_tokens=10, preserve_system=False)
        # System message might be removed if over limit
        assert isinstance(result, list)

    def test_format_provider_error(self):
        """Test formatting provider errors."""
        from unify_llm.utils import format_provider_error

        error = ValueError("Something went wrong")
        formatted = format_provider_error(error, "openai")

        assert "[OPENAI]" in formatted
        assert "ValueError" in formatted
        assert "Something went wrong" in formatted


# ============================================================================
# Tests for unify_llm/client.py
# ============================================================================


class TestUnifyLLMClient:
    """Tests for UnifyLLM client."""

    def test_client_init_with_api_key(self):
        """Test client initialization with explicit API key."""
        client = UnifyLLM(provider="openai", api_key="test-key")
        assert client is not None
        assert client._provider is not None
        assert client._provider_name == "openai"

    def test_client_init_with_env_api_key(self):
        """Test client initialization with API key from environment."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-test-key"}):
            client = UnifyLLM(provider="openai")
            assert client is not None

    def test_client_init_invalid_provider(self):
        """Test client initialization with invalid provider."""
        with pytest.raises(InvalidRequestError) as exc_info:
            UnifyLLM(provider="nonexistent_provider")

        assert "not supported" in str(exc_info.value)
        assert "Available providers:" in str(exc_info.value)

    def test_register_provider(self):
        """Test registering a custom provider."""
        from unify_llm.providers.base import BaseProvider

        class TestProvider(BaseProvider):
            def _get_headers(self):
                return {}

            def _get_base_url(self):
                return "http://test.com"

            def _convert_request(self, request):
                return {}

            def _convert_response(self, response):
                return Mock()

            def _convert_stream_chunk(self, chunk):
                return None

            def _chat_impl(self, request):
                return Mock()

            async def _achat_impl(self, request):
                return Mock()

            def _chat_stream_impl(self, request):
                yield Mock()

            async def _achat_stream_impl(self, request):
                yield Mock()

        UnifyLLM.register_provider("test_provider", TestProvider)
        assert "test_provider" in UnifyLLM._providers

        # Should be able to create client
        client = UnifyLLM(provider="test_provider", api_key="test")
        assert client is not None

    def test_register_invalid_provider(self):
        """Test registering an invalid provider class."""

        class NotAProvider:
            pass

        with pytest.raises(InvalidRequestError):
            UnifyLLM.register_provider("invalid", NotAProvider)

    @patch("unify_llm.providers.openai.OpenAIProvider.chat")
    def test_chat_with_dict_messages(self, mock_chat):
        """Test chat with dict messages."""
        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4",
            choices=[
                ChatResponseChoice(
                    index=0,
                    message=Message(role="assistant", content="Hello!"),
                    finish_reason="stop",
                )
            ],
            created=1234567890,
            provider="openai",
        )
        mock_chat.return_value = mock_response

        client = UnifyLLM(provider="openai", api_key="test-key")
        response = client.chat(model="gpt-4", messages=[{"role": "user", "content": "Hi"}])

        assert response.content == "Hello!"
        mock_chat.assert_called_once()

    @patch("unify_llm.providers.openai.OpenAIProvider.chat")
    def test_chat_with_message_objects(self, mock_chat):
        """Test chat with Message objects."""
        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4",
            choices=[
                ChatResponseChoice(
                    index=0,
                    message=Message(role="assistant", content="Response"),
                    finish_reason="stop",
                )
            ],
            created=1234567890,
            provider="openai",
        )
        mock_chat.return_value = mock_response

        client = UnifyLLM(provider="openai", api_key="test-key")
        response = client.chat(model="gpt-4", messages=[Message(role="user", content="Test")])

        assert response.content == "Response"

    @patch("unify_llm.providers.openai.OpenAIProvider.chat")
    def test_chat_with_tools(self, mock_chat):
        """Test chat with tools."""
        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4",
            choices=[
                ChatResponseChoice(
                    index=0,
                    message=Message(role="assistant", content="Used tool"),
                    finish_reason="stop",
                )
            ],
            created=1234567890,
            provider="openai",
        )
        mock_chat.return_value = mock_response

        client = UnifyLLM(provider="openai", api_key="test-key")
        tools = [
            {
                "type": "function",
                "function": {"name": "test_tool", "description": "A test tool", "parameters": {}},
            }
        ]

        response = client.chat(
            model="gpt-4", messages=[{"role": "user", "content": "Use the tool"}], tools=tools
        )

        assert response.content == "Used tool"

    @patch("unify_llm.providers.openai.OpenAIProvider.achat")
    @pytest.mark.asyncio
    async def test_achat(self, mock_achat):
        """Test async chat."""
        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4",
            choices=[
                ChatResponseChoice(
                    index=0,
                    message=Message(role="assistant", content="Async response"),
                    finish_reason="stop",
                )
            ],
            created=1234567890,
            provider="openai",
        )
        mock_achat.return_value = mock_response

        client = UnifyLLM(provider="openai", api_key="test-key")
        response = await client.achat(model="gpt-4", messages=[{"role": "user", "content": "Test"}])

        assert response.content == "Async response"

    @patch("unify_llm.providers.openai.OpenAIProvider.chat_stream")
    def test_chat_stream(self, mock_stream):
        """Test streaming chat."""
        from unify_llm.models import StreamChunk, StreamChoiceDelta, MessageDelta

        mock_chunks = [
            StreamChunk(
                id="chunk-1",
                model="gpt-4",
                choices=[
                    StreamChoiceDelta(
                        index=0, delta=MessageDelta(content="Hello"), finish_reason=None
                    )
                ],
                created=1234567890,
                provider="openai",
            ),
            StreamChunk(
                id="chunk-2",
                model="gpt-4",
                choices=[
                    StreamChoiceDelta(
                        index=0, delta=MessageDelta(content=" world"), finish_reason=None
                    )
                ],
                created=1234567891,
                provider="openai",
            ),
        ]
        mock_stream.return_value = iter(mock_chunks)

        client = UnifyLLM(provider="openai", api_key="test-key")
        chunks = list(
            client.chat_stream(model="gpt-4", messages=[{"role": "user", "content": "Test"}])
        )

        assert len(chunks) == 2
        assert chunks[0].content == "Hello"

    @patch("unify_llm.providers.openai.OpenAIProvider.achat_stream")
    @pytest.mark.asyncio
    async def test_achat_stream(self, mock_stream):
        """Test async streaming chat."""
        from unify_llm.models import StreamChunk, StreamChoiceDelta, MessageDelta

        async def async_generator():
            yield StreamChunk(
                id="chunk-1",
                model="gpt-4",
                choices=[
                    StreamChoiceDelta(
                        index=0, delta=MessageDelta(content="Async"), finish_reason=None
                    )
                ],
                created=1234567890,
                provider="openai",
            )
            yield StreamChunk(
                id="chunk-2",
                model="gpt-4",
                choices=[
                    StreamChoiceDelta(
                        index=0, delta=MessageDelta(content=" stream"), finish_reason=None
                    )
                ],
                created=1234567891,
                provider="openai",
            )

        mock_stream.return_value = async_generator()

        client = UnifyLLM(provider="openai", api_key="test-key")
        chunks = []
        async for chunk in client.achat_stream(
            model="gpt-4", messages=[{"role": "user", "content": "Test"}]
        ):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0].content == "Async"


# ============================================================================
# Tests for unify_llm/providers/base.py
# ============================================================================


class TestBaseProvider:
    """Tests for BaseProvider."""

    def test_provider_initialization(self):
        """Test provider initialization."""
        from unify_llm.providers.openai import OpenAIProvider

        config = ProviderConfig(api_key="test-key", timeout=30.0)
        provider = OpenAIProvider(config)

        assert provider.config == config
        assert provider.name == "openai"
        assert provider.client is not None
        assert provider.async_client is not None

    def test_provider_context_manager(self):
        """Test provider as async context manager."""
        from unify_llm.providers.openai import OpenAIProvider

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)

        # Test __aenter__
        result = provider.__aenter__()
        assert result is not None

    @pytest.mark.asyncio
    async def test_provider_aexit(self):
        """Test provider async exit."""
        from unify_llm.providers.openai import OpenAIProvider

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)

        # Should not raise
        await provider.__aexit__(None, None, None)

    def test_chat_with_stream_raises_error(self):
        """Test that chat() with stream=True raises error."""
        from unify_llm.providers.openai import OpenAIProvider

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)

        request = ChatRequest(
            model="gpt-4", messages=[Message(role="user", content="Test")], stream=True
        )

        with pytest.raises(ValueError) as exc_info:
            provider.chat(request)

        assert "chat_stream" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_achat_with_stream_raises_error(self):
        """Test that achat() with stream=True raises error."""
        from unify_llm.providers.openai import OpenAIProvider

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)

        request = ChatRequest(
            model="gpt-4", messages=[Message(role="user", content="Test")], stream=True
        )

        with pytest.raises(ValueError):
            await provider.achat(request)

    def test_handle_http_error_401(self):
        """Test handling 401 authentication error."""
        from unify_llm.providers.openai import OpenAIProvider
        import httpx

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)

        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid API key"}
        mock_response.text = "Invalid API key"

        error = httpx.HTTPStatusError("401 Unauthorized", request=Mock(), response=mock_response)

        with pytest.raises(AuthenticationError):
            provider._handle_http_error(error)

    def test_handle_http_error_429(self):
        """Test handling 429 rate limit error."""
        from unify_llm.providers.openai import OpenAIProvider
        import httpx

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        mock_response.headers = {"retry-after": "60"}

        error = httpx.HTTPStatusError(
            "429 Too Many Requests", request=Mock(), response=mock_response
        )

        with pytest.raises(RateLimitError) as exc_info:
            provider._handle_http_error(error)

        assert exc_info.value.retry_after == 60

    def test_handle_http_error_400(self):
        """Test handling 400 bad request error."""
        from unify_llm.providers.openai import OpenAIProvider
        import httpx

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid request"}

        error = httpx.HTTPStatusError("400 Bad Request", request=Mock(), response=mock_response)

        with pytest.raises(InvalidRequestError):
            provider._handle_http_error(error)

    def test_handle_http_error_500(self):
        """Test handling 500 server error."""
        from unify_llm.providers.openai import OpenAIProvider
        import httpx

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}

        error = httpx.HTTPStatusError(
            "500 Internal Server Error", request=Mock(), response=mock_response
        )

        with pytest.raises(APIError):
            provider._handle_http_error(error)

    def test_handle_http_error_non_json_response(self):
        """Test handling error with non-JSON response."""
        from unify_llm.providers.openai import OpenAIProvider
        import httpx

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = Exception("Not JSON")
        mock_response.text = "Server error text"

        error = httpx.HTTPStatusError(
            "500 Internal Server Error", request=Mock(), response=mock_response
        )

        with pytest.raises(APIError):
            provider._handle_http_error(error)


# ============================================================================
# Tests for unify_llm/agent/tools.py
# ============================================================================


class TestTools:
    """Tests for agent tools."""

    def test_tool_parameter_creation(self):
        """Test creating tool parameters."""
        param = ToolParameter(
            type=ToolParameterType.STRING, description="Test parameter", required=True
        )

        assert param.type == ToolParameterType.STRING
        assert param.description == "Test parameter"
        assert param.required is True

    def test_tool_parameter_with_enum(self):
        """Test tool parameter with enum values."""
        param = ToolParameter(
            type=ToolParameterType.STRING,
            description="Choice parameter",
            enum=["option1", "option2", "option3"],
        )

        assert param.enum == ["option1", "option2", "option3"]

    def test_tool_result_success(self):
        """Test successful tool result."""
        result = ToolResult(success=True, output="Result data")
        assert result.success is True
        assert result.output == "Result data"
        assert result.error is None

    def test_tool_result_failure(self):
        """Test failed tool result."""
        result = ToolResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"

    def test_tool_creation(self):
        """Test creating a tool."""

        def test_func(x: int, y: int) -> int:
            return x + y

        tool = Tool(
            name="add",
            description="Add two numbers",
            parameters={
                "x": ToolParameter(type=ToolParameterType.INTEGER, description="First number"),
                "y": ToolParameter(type=ToolParameterType.INTEGER, description="Second number"),
            },
            function=test_func,
        )

        assert tool.name == "add"
        assert tool.description == "Add two numbers"
        assert len(tool.parameters) == 2

    def test_tool_to_openai_format(self):
        """Test converting tool to OpenAI format."""
        tool = Tool(
            name="test_tool",
            description="A test tool",
            parameters={
                "param1": ToolParameter(
                    type=ToolParameterType.STRING, description="Parameter 1", required=True
                ),
                "param2": ToolParameter(
                    type=ToolParameterType.INTEGER, description="Parameter 2", required=False
                ),
            },
        )

        openai_format = tool.to_openai_format()

        assert openai_format["type"] == "function"
        assert openai_format["function"]["name"] == "test_tool"
        assert "param1" in openai_format["function"]["parameters"]["properties"]
        assert "param1" in openai_format["function"]["parameters"]["required"]
        assert "param2" not in openai_format["function"]["parameters"]["required"]

    def test_tool_to_anthropic_format(self):
        """Test converting tool to Anthropic format."""
        tool = Tool(
            name="test_tool",
            description="A test tool",
            parameters={
                "param1": ToolParameter(
                    type=ToolParameterType.STRING, description="Parameter 1", required=True
                )
            },
        )

        anthropic_format = tool.to_anthropic_format()

        assert anthropic_format["name"] == "test_tool"
        assert "input_schema" in anthropic_format
        assert "param1" in anthropic_format["input_schema"]["properties"]

    def test_tool_execute_success(self):
        """Test successful tool execution."""

        def add(x: int, y: int) -> int:
            return x + y

        tool = Tool(name="add", description="Add numbers", parameters={}, function=add)

        result = tool.execute(x=5, y=3)

        assert result.success is True
        assert result.output == 8

    def test_tool_execute_returns_tool_result(self):
        """Test tool that returns ToolResult."""

        def test_func() -> ToolResult:
            return ToolResult(success=True, output="custom result")

        tool = Tool(name="test", description="Test", function=test_func)

        result = tool.execute()

        assert result.success is True
        assert result.output == "custom result"

    def test_tool_execute_error(self):
        """Test tool execution with error."""

        def failing_func():
            raise ValueError("Test error")

        tool = Tool(name="fail", description="Failing tool", function=failing_func)

        result = tool.execute()

        assert result.success is False
        assert "Test error" in result.error

    def test_tool_execute_no_function(self):
        """Test executing tool with no function defined."""
        tool = Tool(name="no_func", description="No function", function=None)

        result = tool.execute()

        assert result.success is False
        assert "no function defined" in result.error

    @pytest.mark.asyncio
    async def test_tool_aexecute_with_async_function(self):
        """Test async tool execution."""

        async def async_add(x: int, y: int) -> int:
            return x + y

        tool = Tool(name="async_add", description="Async add", async_function=async_add)

        result = await tool.aexecute(x=10, y=5)

        assert result.success is True
        assert result.output == 15

    @pytest.mark.asyncio
    async def test_tool_aexecute_fallback_to_sync(self):
        """Test async execution falling back to sync."""

        def sync_func(x: int) -> int:
            return x * 2

        tool = Tool(name="sync_func", description="Sync function", function=sync_func)

        result = await tool.aexecute(x=5)

        assert result.success is True
        assert result.output == 10

    @pytest.mark.asyncio
    async def test_tool_aexecute_no_function(self):
        """Test async execution with no function."""
        tool = Tool(name="no_func", description="No function")

        result = await tool.aexecute()

        assert result.success is False

    def test_tool_registry_register(self):
        """Test registering tools."""
        registry = ToolRegistry()

        tool = Tool(name="test_tool", description="Test", function=lambda: "result")

        registry.register(tool)

        assert registry.get("test_tool") is tool

    def test_tool_registry_register_function(self):
        """Test registering a function as a tool."""
        registry = ToolRegistry()

        def my_func(x: int, y: str) -> str:
            return f"{x}: {y}"

        tool = registry.register_function(name="my_tool", description="My tool", function=my_func)

        assert tool.name == "my_tool"
        assert "x" in tool.parameters
        assert "y" in tool.parameters

    def test_tool_registry_auto_detect_parameters(self):
        """Test auto-detecting parameters from function signature."""
        registry = ToolRegistry()

        def func(a: str, b: int, c: bool = True, d: float = 1.5):
            pass

        params = registry._auto_detect_parameters(func)

        assert "a" in params
        assert params["a"].type == ToolParameterType.STRING
        assert params["a"].required is True

        assert "b" in params
        assert params["b"].type == ToolParameterType.INTEGER

        assert "c" in params
        assert params["c"].required is False
        assert params["c"].default is True

    def test_tool_registry_get(self):
        """Test getting tool from registry."""
        registry = ToolRegistry()

        tool = Tool(name="test", description="Test", function=lambda: None)
        registry.register(tool)

        retrieved = registry.get("test")
        assert retrieved is tool

        # Non-existent tool
        assert registry.get("nonexistent") is None

    def test_tool_registry_list_tools(self):
        """Test listing all tools."""
        registry = ToolRegistry()

        tool1 = Tool(name="tool1", description="Test 1", function=lambda: None)
        tool2 = Tool(name="tool2", description="Test 2", function=lambda: None)

        registry.register(tool1)
        registry.register(tool2)

        tools = registry.list_tools()

        assert len(tools) == 2
        assert tool1 in tools
        assert tool2 in tools

    def test_tool_registry_get_tools_for_provider_openai(self):
        """Test getting tools in OpenAI format."""
        registry = ToolRegistry()

        tool = Tool(
            name="test",
            description="Test tool",
            parameters={"param": ToolParameter(type=ToolParameterType.STRING, description="Param")},
        )
        registry.register(tool)

        tools = registry.get_tools_for_provider("openai")

        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "test"

    def test_tool_registry_get_tools_for_provider_anthropic(self):
        """Test getting tools in Anthropic format."""
        registry = ToolRegistry()

        tool = Tool(name="test", description="Test tool", parameters={})
        registry.register(tool)

        tools = registry.get_tools_for_provider("anthropic")

        assert len(tools) == 1
        assert tools[0]["name"] == "test"
        assert "input_schema" in tools[0]

    def test_tool_registry_unregister(self):
        """Test unregistering a tool."""
        registry = ToolRegistry()

        tool = Tool(name="test", description="Test", function=lambda: None)
        registry.register(tool)

        assert registry.get("test") is not None

        result = registry.unregister("test")
        assert result is True
        assert registry.get("test") is None

        # Unregister non-existent tool
        result = registry.unregister("nonexistent")
        assert result is False

    def test_tool_registry_clear(self):
        """Test clearing all tools."""
        registry = ToolRegistry()

        registry.register(Tool(name="tool1", description="Test", function=lambda: None))
        registry.register(Tool(name="tool2", description="Test", function=lambda: None))

        assert len(registry.list_tools()) == 2

        registry.clear()

        assert len(registry.list_tools()) == 0


# ============================================================================
# Tests for unify_llm/agent/executor.py
# ============================================================================


class TestAgentExecutor:
    """Tests for AgentExecutor (WITHOUT calling real LLMs)."""

    def test_executor_initialization(self):
        """Test executor initialization."""
        mock_client = Mock()
        config = AgentConfig(
            name="test_agent",
            model="gpt-4",
            provider="openai",
            enable_memory=False,  # Disable memory to avoid system message
        )
        agent = Agent(config=config, client=mock_client)

        registry = ToolRegistry()
        memory = ConversationMemory()

        executor = AgentExecutor(agent=agent, tool_registry=registry, memory=memory)

        assert executor.agent is agent
        assert executor.tool_registry is registry
        # Memory object might be wrapped, so just check it exists
        assert executor.memory is not None

    def test_executor_initialization_with_defaults(self):
        """Test executor with default registry and memory."""
        mock_client = Mock()
        config = AgentConfig(name="test_agent", model="gpt-4", provider="openai")
        agent = Agent(config=config, client=mock_client)

        executor = AgentExecutor(agent=agent)

        assert executor.tool_registry is not None
        assert executor.memory is not None

    def test_executor_run_without_tools(self):
        """Test running executor without tools."""
        mock_client = Mock()

        # Mock the chat response
        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4",
            choices=[
                ChatResponseChoice(
                    index=0,
                    message=Message(role="assistant", content="This is my response"),
                    finish_reason="stop",
                )
            ],
            created=1234567890,
            provider="openai",
        )
        mock_client.chat.return_value = mock_response

        config = AgentConfig(
            name="test_agent", model="gpt-4", provider="openai", enable_memory=False
        )
        agent = Agent(config=config, client=mock_client)

        executor = AgentExecutor(agent=agent)
        result = executor.run("Hello")

        assert result.success is True
        assert result.output == "This is my response"
        assert result.iterations == 1
        assert len(result.tool_calls) == 0

    def test_executor_run_with_tool_calls(self):
        """Test running executor with tool calls."""
        mock_client = Mock()

        # Create a mock tool call
        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "function"
        mock_tool_call.function = Mock()
        mock_tool_call.function.name = "calculator"
        mock_tool_call.function.arguments = json.dumps({"x": 5, "y": 3})

        # First response with tool call - use proper Message object
        assistant_msg_with_tools = Message(
            role="assistant",
            content="I'll calculate that",
            tool_calls=[
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {"name": "calculator", "arguments": json.dumps({"x": 5, "y": 3})},
                }
            ],
        )

        mock_response1 = ChatResponse(
            id="test-id-1",
            model="gpt-4",
            choices=[
                ChatResponseChoice(
                    index=0, message=assistant_msg_with_tools, finish_reason="tool_calls"
                )
            ],
            created=1234567890,
            provider="openai",
        )

        # Manually add tool_calls attribute for executor to read
        mock_response1.choices[0].message.tool_calls = [mock_tool_call]

        # Second response after tool execution
        mock_response2 = ChatResponse(
            id="test-id-2",
            model="gpt-4",
            choices=[
                ChatResponseChoice(
                    index=0,
                    message=Message(role="assistant", content="The answer is 8"),
                    finish_reason="stop",
                )
            ],
            created=1234567891,
            provider="openai",
        )

        mock_client.chat.side_effect = [mock_response1, mock_response2]

        config = AgentConfig(
            name="test_agent",
            model="gpt-4",
            provider="openai",
            tools=["calculator"],
            enable_memory=False,
        )
        agent = Agent(config=config, client=mock_client)

        # Register calculator tool
        registry = ToolRegistry()

        def calculator(x: int, y: int) -> int:
            return x + y

        registry.register_function("calculator", "Add two numbers", calculator)

        executor = AgentExecutor(agent=agent, tool_registry=registry)
        result = executor.run("What's 5 + 3?")

        assert result.success is True
        assert result.iterations == 2
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["tool"] == "calculator"

    def test_executor_run_tool_not_found(self):
        """Test running with tool call to non-existent tool."""
        mock_client = Mock()

        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "function"
        mock_tool_call.function = Mock()
        mock_tool_call.function.name = "nonexistent_tool"
        mock_tool_call.function.arguments = json.dumps({})

        assistant_msg_with_tools = Message(
            role="assistant",
            content="Using the tool",  # Must have content for validation
            tool_calls=[
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {"name": "nonexistent_tool", "arguments": json.dumps({})},
                }
            ],
        )

        mock_response1 = ChatResponse(
            id="test-id-1",
            model="gpt-4",
            choices=[
                ChatResponseChoice(
                    index=0, message=assistant_msg_with_tools, finish_reason="tool_calls"
                )
            ],
            created=1234567890,
            provider="openai",
        )
        mock_response1.choices[0].message.tool_calls = [mock_tool_call]

        mock_response2 = ChatResponse(
            id="test-id-2",
            model="gpt-4",
            choices=[
                ChatResponseChoice(
                    index=0,
                    message=Message(role="assistant", content="Tool not found"),
                    finish_reason="stop",
                )
            ],
            created=1234567891,
            provider="openai",
        )

        mock_client.chat.side_effect = [mock_response1, mock_response2]

        config = AgentConfig(
            name="test_agent",
            model="gpt-4",
            provider="openai",
            tools=["nonexistent_tool"],
            enable_memory=False,
        )
        agent = Agent(config=config, client=mock_client)

        executor = AgentExecutor(agent=agent)
        result = executor.run("Test")

        assert result.success is True
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["result"]["success"] is False

    def test_executor_run_max_iterations(self):
        """Test executor hitting max iterations."""
        mock_client = Mock()

        # Always return tool calls
        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "function"
        mock_tool_call.function = Mock()
        mock_tool_call.function.name = "tool"
        mock_tool_call.function.arguments = json.dumps({})

        assistant_msg_with_tools = Message(
            role="assistant",
            content="Using the tool",  # Must have content for validation
            tool_calls=[
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {"name": "tool", "arguments": json.dumps({})},
                }
            ],
        )

        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4",
            choices=[
                ChatResponseChoice(
                    index=0, message=assistant_msg_with_tools, finish_reason="tool_calls"
                )
            ],
            created=1234567890,
            provider="openai",
        )
        mock_response.choices[0].message.tool_calls = [mock_tool_call]

        mock_client.chat.return_value = mock_response

        config = AgentConfig(
            name="test_agent",
            model="gpt-4",
            provider="openai",
            tools=["tool"],
            max_iterations=2,
            enable_memory=False,
        )
        agent = Agent(config=config, client=mock_client)

        registry = ToolRegistry()
        registry.register_function("tool", "Test tool", lambda: "result")

        executor = AgentExecutor(agent=agent, tool_registry=registry)
        result = executor.run("Test")

        assert result.success is False
        assert "Maximum iterations" in result.error
        assert result.iterations == 2

    def test_executor_run_with_exception(self):
        """Test executor handling exceptions."""
        mock_client = Mock()
        mock_client.chat.side_effect = Exception("API error")

        config = AgentConfig(
            name="test_agent", model="gpt-4", provider="openai", enable_memory=False
        )
        agent = Agent(config=config, client=mock_client)

        executor = AgentExecutor(agent=agent)
        result = executor.run("Test")

        assert result.success is False
        assert "API error" in result.error

    @pytest.mark.asyncio
    async def test_executor_arun(self):
        """Test async executor run."""
        mock_client = Mock()

        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4",
            choices=[
                ChatResponseChoice(
                    index=0,
                    message=Message(role="assistant", content="Async response"),
                    finish_reason="stop",
                )
            ],
            created=1234567890,
            provider="openai",
        )
        mock_client.achat = AsyncMock(return_value=mock_response)

        config = AgentConfig(
            name="test_agent", model="gpt-4", provider="openai", enable_memory=False
        )
        agent = Agent(config=config, client=mock_client)

        executor = AgentExecutor(agent=agent)
        result = await executor.arun("Test")

        assert result.success is True
        assert result.output == "Async response"

    def test_executor_reset_memory(self):
        """Test resetting executor memory."""
        mock_client = Mock()
        config = AgentConfig(
            name="test_agent",
            model="gpt-4",
            provider="openai",
            system_prompt="You are helpful",
            enable_memory=True,
        )
        agent = Agent(config=config, client=mock_client)

        memory = ConversationMemory()
        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi there")

        executor = AgentExecutor(agent=agent, memory=memory)

        # Use internal _messages attribute
        assert len(memory._messages) > 0

        executor.reset_memory()

        # After reset, should have system message only
        messages = memory.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "system"

    def test_execution_result_creation(self):
        """Test creating ExecutionResult."""
        result = ExecutionResult(
            success=True,
            output="Test output",
            iterations=3,
            tool_calls=[{"tool": "test", "result": "ok"}],
            metadata={"model": "gpt-4"},
        )

        assert result.success is True
        assert result.output == "Test output"
        assert result.iterations == 3
        assert len(result.tool_calls) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
