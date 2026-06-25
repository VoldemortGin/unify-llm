"""MCP Protocol definitions and message structures."""


from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    """Types of resources that can be exposed via MCP."""
    TEXT = "text"
    BLOB = "blob"
    IMAGE = "image"
    DIRECTORY = "directory"


class MCPMessage(BaseModel):
    """Base MCP message structure."""
    jsonrpc: str = "2.0"
    id: str | int | None = None


class MCPRequest(MCPMessage):
    """MCP request message."""
    method: str
    params: dict[str, Any] | None = None


class MCPResponse(MCPMessage):
    """MCP response message."""
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class MCPNotification(BaseModel):
    """MCP notification message (no response expected)."""
    jsonrpc: str = "2.0"
    method: str
    params: dict[str, Any] | None = None


class ToolDefinition(BaseModel):
    """Definition of a tool exposed via MCP."""
    name: str
    description: str
    input_schema: dict[str, Any]


class PromptDefinition(BaseModel):
    """Definition of a prompt template exposed via MCP."""
    name: str
    description: str
    arguments: list[dict[str, Any]] = Field(default_factory=list)


class ResourceDefinition(BaseModel):
    """Definition of a resource exposed via MCP."""
    uri: str
    name: str
    description: str
    mime_type: str
    type: ResourceType


class ServerCapabilities(BaseModel):
    """Capabilities advertised by an MCP server."""
    tools: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    prompts: dict[str, Any] | None = None
    logging: dict[str, Any] | None = None


class ClientCapabilities(BaseModel):
    """Capabilities advertised by an MCP client."""
    roots: dict[str, Any] | None = None
    sampling: dict[str, Any] | None = None


class InitializeParams(BaseModel):
    """Parameters for the initialize request."""
    protocol_version: str
    capabilities: ClientCapabilities
    client_info: dict[str, str]


class InitializeResult(BaseModel):
    """Result of the initialize request."""
    protocol_version: str
    capabilities: ServerCapabilities
    server_info: dict[str, str]
