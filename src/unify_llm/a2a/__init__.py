"""
Agent-to-Agent (A2A) Protocol Implementation for UnifyLLM

This module provides A2A protocol for enabling multiple AI agents to communicate
and collaborate with each other.
"""


from __future__ import annotations

from unify_llm.a2a.agent_comm import (
    A2AAgent,
    A2AAgentConfig,
    AgentDiscovery,
    AgentRegistry,
)
from unify_llm.a2a.collaboration import (
    AgentCollaboration,
    CollaborationStrategy,
    ConsensusBuilder,
    TaskDelegation,
)
from unify_llm.a2a.message_bus import (
    DistributedMessageBus,
    MessageBus,
    MessageBusConfig,
)
from unify_llm.a2a.protocol import (
    A2AMessage,
    A2ARequest,
    A2AResponse,
    AgentCapability,
    AgentStatus,
    TaskRequest,
    TaskResponse,
)

__all__ = [
    # Protocol
    "A2AMessage",
    "A2ARequest",
    "A2AResponse",
    "AgentCapability",
    "TaskRequest",
    "TaskResponse",
    "AgentStatus",
    # Agent Communication
    "A2AAgent",
    "A2AAgentConfig",
    "AgentRegistry",
    "AgentDiscovery",
    # Collaboration
    "AgentCollaboration",
    "CollaborationStrategy",
    "TaskDelegation",
    "ConsensusBuilder",
    # Message Bus
    "MessageBus",
    "MessageBusConfig",
    "DistributedMessageBus",
]
