"""MCP Protocol definitions and message structures."""

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
    id: Optional[Union[str, int]] = None


class MCPRequest(MCPMessage):
    """MCP request message."""
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(MCPMessage):
    """MCP response message."""
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class MCPNotification(BaseModel):
    """MCP notification message (no response expected)."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None


class ToolDefinition(BaseModel):
    """Definition of a tool exposed via MCP."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class PromptDefinition(BaseModel):
    """Definition of a prompt template exposed via MCP."""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = Field(default_factory=list)


class ResourceDefinition(BaseModel):
    """Definition of a resource exposed via MCP."""
    uri: str
    name: str
    description: str
    mime_type: str
    type: ResourceType


class ServerCapabilities(BaseModel):
    """Capabilities advertised by an MCP server."""
    tools: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None


class ClientCapabilities(BaseModel):
    """Capabilities advertised by an MCP client."""
    roots: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None


class InitializeParams(BaseModel):
    """Parameters for the initialize request."""
    protocol_version: str
    capabilities: ClientCapabilities
    client_info: Dict[str, str]


class InitializeResult(BaseModel):
    """Result of the initialize request."""
    protocol_version: str
    capabilities: ServerCapabilities
    server_info: Dict[str, str]
