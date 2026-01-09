"""
UnifyLLM - Unified LLM API Library with AI Agent Framework

A unified interface for multiple LLM providers including OpenAI, Anthropic, Gemini, and Ollama.
Now with powerful AI Agent capabilities inspired by n8n!
"""

# Core client
# A2A (Agent-to-Agent Protocol)
from src.a2a import (
    A2AAgent,
    A2AAgentConfig,
    AgentCollaboration,
    AgentDiscovery,
    AgentRegistry,
    CollaborationStrategy,
    ConsensusBuilder,
    DistributedMessageBus,
    MessageBus,
    MessageBusConfig,
    TaskDelegation,
)

# AI Agent Framework
from src.agent import (
    Agent,
    AgentConfig,
    AgentExecutor,
    ConversationMemory,
    MemoryMessage,
    Tool,
    ToolRegistry,
    ToolResult,
    Workflow,
    WorkflowConfig,
    WorkflowNode,
)
from src.client import UnifyLLM

# Configuration (for advanced users)
from src.core.config import Settings, settings

# Exceptions
from src.core.exceptions import (
    APIError,
    AuthenticationError,
    ContentFilterError,
    InvalidRequestError,
    ModelNotFoundError,
    ProviderError,
    RateLimitError,
    TimeoutError,
    UnifyLLMError,
)

# MCP (Model Context Protocol)
from src.mcp import (
    MCPClient,
    MCPClientConfig,
    MCPServer,
    MCPServerConfig,
    MCPTransport,
    SSETransport,
    StdioTransport,
    WebSocketTransport,
)

# Data models
from src.models import (
    ChatRequest,
    ChatResponse,
    ChatResponseChoice,
    Message,
    MessageDelta,
    ProviderConfig,
    StreamChoiceDelta,
    StreamChunk,
    Usage,
)

# Utilities
from src.utils import (
    estimate_tokens,
    format_provider_error,
    get_api_key_from_env,
    truncate_messages,
)

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
    # AI Agent
    "Agent",
    "AgentConfig",
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "ConversationMemory",
    "MemoryMessage",
    "AgentExecutor",
    "Workflow",
    "WorkflowNode",
    "WorkflowConfig",
    # MCP
    "MCPClient",
    "MCPClientConfig",
    "MCPServer",
    "MCPServerConfig",
    "MCPTransport",
    "StdioTransport",
    "SSETransport",
    "WebSocketTransport",
    # A2A
    "A2AAgent",
    "A2AAgentConfig",
    "AgentRegistry",
    "AgentDiscovery",
    "AgentCollaboration",
    "CollaborationStrategy",
    "TaskDelegation",
    "ConsensusBuilder",
    "MessageBus",
    "MessageBusConfig",
    "DistributedMessageBus",
]
