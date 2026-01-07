"""AI Agent functionality for UnifyLLM.

This module provides a flexible AI agent framework inspired by n8n,
enabling tool-based agents, multi-agent workflows, and memory management.

New n8n-style features:
- Triggers (Schedule, Webhook, Interval, Manual)
- HTTP Request node
- Webhook server
- Execution history and persistence
"""

from unify_llm.agent.base import Agent, AgentConfig, AgentType
from unify_llm.agent.tools import Tool, ToolResult, ToolRegistry, ToolParameter, ToolParameterType
from unify_llm.agent.memory import ConversationMemory, MemoryMessage, SharedMemory
from unify_llm.agent.executor import AgentExecutor, ExecutionResult
from unify_llm.agent.workflow import Workflow, WorkflowNode, WorkflowConfig, NodeType, WorkflowResult

# Advanced features
from unify_llm.agent.advanced import ParallelExecutor, ErrorHandler, AgentChain

# Templates
from unify_llm.agent.templates import AgentTemplates

# Visualization
from unify_llm.agent.visualization import WorkflowVisualizer, ExecutionTracer, visualize_workflow

# Monitoring
from unify_llm.agent.monitoring import (
    PerformanceMonitor,
    ExecutionLogger,
    AgentMetrics,
    get_monitor,
    get_logger
)

# n8n-style features
from unify_llm.agent.triggers import (
    TriggerType,
    TriggerStatus,
    TriggerEvent,
    TriggerConfig,
    BaseTrigger,
    ScheduleTrigger,
    IntervalTrigger,
    WebhookTrigger,
    ManualTrigger,
    TriggerManager
)

from unify_llm.agent.http_tools import (
    http_request,
    http_get,
    http_post,
    http_put,
    http_delete,
    create_http_request_tool,
    create_all_http_tools
)

from unify_llm.agent.webhook_server import WebhookServer, WebhookClient

from unify_llm.agent.execution_history import (
    ExecutionStatus,
    ExecutionData,
    ExecutionHistory
)

__all__ = [
    # Core
    "Agent",
    "AgentConfig",
    "AgentType",
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "ToolParameter",
    "ToolParameterType",
    "ConversationMemory",
    "MemoryMessage",
    "SharedMemory",
    "AgentExecutor",
    "ExecutionResult",
    "Workflow",
    "WorkflowNode",
    "WorkflowConfig",
    "NodeType",
    "WorkflowResult",
    # Advanced
    "ParallelExecutor",
    "ErrorHandler",
    "AgentChain",
    # Templates
    "AgentTemplates",
    # Visualization
    "WorkflowVisualizer",
    "ExecutionTracer",
    "visualize_workflow",
    # Monitoring
    "PerformanceMonitor",
    "ExecutionLogger",
    "AgentMetrics",
    "get_monitor",
    "get_logger",
    # Triggers (n8n-style)
    "TriggerType",
    "TriggerStatus",
    "TriggerEvent",
    "TriggerConfig",
    "BaseTrigger",
    "ScheduleTrigger",
    "IntervalTrigger",
    "WebhookTrigger",
    "ManualTrigger",
    "TriggerManager",
    # HTTP Tools (n8n-style)
    "http_request",
    "http_get",
    "http_post",
    "http_put",
    "http_delete",
    "create_http_request_tool",
    "create_all_http_tools",
    # Webhook Server (n8n-style)
    "WebhookServer",
    "WebhookClient",
    # Execution History (n8n-style)
    "ExecutionStatus",
    "ExecutionData",
    "ExecutionHistory",
]
