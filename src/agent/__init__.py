"""AI Agent functionality for UnifyLLM.

This module provides a flexible AI agent framework inspired by n8n,
enabling tool-based agents, multi-agent workflows, and memory management.

New n8n-style features:
- Triggers (Schedule, Webhook, Interval, Manual)
- HTTP Request node
- Webhook server
- Execution history and persistence
"""

# Advanced features
from src.agent.advanced import AgentChain, ErrorHandler, ParallelExecutor
from src.agent.base import Agent, AgentConfig, AgentType
from src.agent.execution_history import ExecutionData, ExecutionHistory, ExecutionStatus
from src.agent.executor import AgentExecutor, ExecutionResult
from src.agent.http_tools import (
    create_all_http_tools,
    create_http_request_tool,
    http_delete,
    http_get,
    http_post,
    http_put,
    http_request,
)
from src.agent.memory import ConversationMemory, MemoryMessage, SharedMemory

# Monitoring
from src.agent.monitoring import (
    AgentMetrics,
    ExecutionLogger,
    PerformanceMonitor,
    get_logger,
    get_monitor,
)

# Templates
from src.agent.templates import AgentTemplates
from src.agent.tools import Tool, ToolParameter, ToolParameterType, ToolRegistry, ToolResult

# n8n-style features
from src.agent.triggers import (
    BaseTrigger,
    IntervalTrigger,
    ManualTrigger,
    ScheduleTrigger,
    TriggerConfig,
    TriggerEvent,
    TriggerManager,
    TriggerStatus,
    TriggerType,
    WebhookTrigger,
)

# Visualization
from src.agent.visualization import ExecutionTracer, WorkflowVisualizer, visualize_workflow
from src.agent.webhook_server import WebhookClient, WebhookServer
from src.agent.workflow import NodeType, Workflow, WorkflowConfig, WorkflowNode, WorkflowResult

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
