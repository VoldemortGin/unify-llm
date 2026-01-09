"""A2A Protocol definitions and message structures."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Status of an agent."""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


class AgentCapability(BaseModel):
    """Capability description for an agent."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    tags: List[str] = Field(default_factory=list)


class A2AMessage(BaseModel):
    """Base A2A message structure."""
    id: str
    sender_id: str
    receiver_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    message_type: str


class A2ARequest(A2AMessage):
    """A2A request message."""
    message_type: str = "request"
    method: str
    params: Optional[Dict[str, Any]] = None


class A2AResponse(A2AMessage):
    """A2A response message."""
    message_type: str = "response"
    request_id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class TaskRequest(BaseModel):
    """Request to delegate a task to another agent."""
    task_id: str
    capability: str
    input_data: Dict[str, Any]
    priority: int = 5
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    """Response from a delegated task."""
    task_id: str
    success: bool
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class AgentInfo(BaseModel):
    """Information about an agent."""
    agent_id: str
    agent_name: str
    capabilities: List[AgentCapability]
    status: AgentStatus
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_seen: datetime = Field(default_factory=datetime.now)


class DiscoveryRequest(A2AMessage):
    """Request to discover agents with specific capabilities."""
    message_type: str = "discovery"
    required_capabilities: List[str]
    filters: Dict[str, Any] = Field(default_factory=dict)


class DiscoveryResponse(A2AMessage):
    """Response with discovered agents."""
    message_type: str = "discovery_response"
    agents: List[AgentInfo]


class HeartbeatMessage(BaseModel):
    """Heartbeat message to indicate agent is alive."""
    agent_id: str
    status: AgentStatus
    timestamp: datetime = Field(default_factory=datetime.now)
