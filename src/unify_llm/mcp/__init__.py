"""
Model Context Protocol (MCP) Implementation for UnifyLLM

This module provides MCP client and server implementations for connecting
AI agents to external tools and resources following the MCP specification.
"""


from __future__ import annotations

from unify_llm.mcp.client import MCPClient, MCPClientConfig
from unify_llm.mcp.protocol import (
    MCPMessage,
    MCPNotification,
    MCPRequest,
    MCPResponse,
    PromptDefinition,
    ResourceType,
    ToolDefinition,
)
from unify_llm.mcp.server import MCPServer, MCPServerConfig
from unify_llm.mcp.transport import (
    MCPTransport,
    SSETransport,
    StdioTransport,
    WebSocketTransport,
)

__all__ = [
    # Client
    "MCPClient",
    "MCPClientConfig",
    # Server
    "MCPServer",
    "MCPServerConfig",
    # Transport
    "MCPTransport",
    "StdioTransport",
    "SSETransport",
    "WebSocketTransport",
    # Protocol
    "MCPMessage",
    "MCPRequest",
    "MCPResponse",
    "MCPNotification",
    "ResourceType",
    "ToolDefinition",
    "PromptDefinition",
]
