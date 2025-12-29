"""
UnifyLLM - Unified LLM API Library

A unified interface for multiple LLM providers including OpenAI, Anthropic, Gemini, and Ollama.
"""

# Core client
from unify_llm.client import UnifyLLM

# Data models
from unify_llm.models import (
    Message,
    ChatRequest,
    ChatResponse,
    ChatResponseChoice,
    StreamChunk,
    StreamChoiceDelta,
    MessageDelta,
    Usage,
    ProviderConfig,
)

# Exceptions
from unify_llm.exceptions import (
    UnifyLLMError,
    AuthenticationError,
    RateLimitError,
    InvalidRequestError,
    APIError,
    TimeoutError,
    ModelNotFoundError,
    ContentFilterError,
    ProviderError,
)

# Utilities
from unify_llm.utils import (
    get_api_key_from_env,
    estimate_tokens,
    truncate_messages,
    format_provider_error,
)

# Configuration (for advanced users)
from unify_llm.core.config import settings, Settings

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Client
    "UnifyLLM",
    # Models
    "Message",
    "ChatRequest",
    "ChatResponse",
    "ChatResponseChoice",
    "StreamChunk",
    "StreamChoiceDelta",
    "MessageDelta",
    "Usage",
    "ProviderConfig",
    # Exceptions
    "UnifyLLMError",
    "AuthenticationError",
    "RateLimitError",
    "InvalidRequestError",
    "APIError",
    "TimeoutError",
    "ModelNotFoundError",
    "ContentFilterError",
    "ProviderError",
    # Utilities
    "get_api_key_from_env",
    "estimate_tokens",
    "truncate_messages",
    "format_provider_error",
    # Config
    "settings",
    "Settings",
]
