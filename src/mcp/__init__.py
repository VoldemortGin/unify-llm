"""
Model Context Protocol (MCP) Implementation for UnifyLLM

This module provides MCP client and server implementations for connecting
AI agents to external tools and resources following the MCP specification.
"""

from src.mcp.client import MCPClient, MCPClientConfig
from src.mcp.protocol import (
    MCPMessage,
    MCPNotification,
    MCPRequest,
    MCPResponse,
    PromptDefinition,
    ResourceType,
    ToolDefinition,
)
from src.mcp.server import MCPServer, MCPServerConfig
from src.mcp.transport import (
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
