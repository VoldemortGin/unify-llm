"""Base agent classes and configuration."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class AgentType(str, Enum):
    """Types of agents supported."""
    TOOLS = "tools"  # Agent that can select and use tools
    CONVERSATIONAL = "conversational"  # Simple conversational agent
    ROUTER = "router"  # Routes requests to different workflows
    HIERARCHICAL = "hierarchical"  # Manages sub-agents


class AgentConfig(BaseModel):
    """Configuration for an AI agent.

    Attributes:
        name: Unique identifier for the agent
        agent_type: Type of agent (tools, conversational, router, hierarchical)
        model: LLM model to use (e.g., "gpt-4", "claude-3-opus")
        provider: LLM provider (e.g., "openai", "anthropic")
        system_prompt: System instructions for the agent
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens in response
        max_iterations: Maximum tool calling iterations
        enable_memory: Whether to enable conversation memory
        memory_window: Number of messages to keep in memory
        tools: List of tool names available to the agent
        metadata: Additional metadata for the agent
    """

    name: str = Field(..., description="Unique identifier for the agent")
    agent_type: AgentType = Field(default=AgentType.TOOLS, description="Type of agent")
    model: str = Field(..., description="LLM model to use")
    provider: str = Field(..., description="LLM provider")
    system_prompt: str = Field(
        default="You are a helpful AI assistant.",
        description="System instructions for the agent"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens in response")
    max_iterations: int = Field(default=10, ge=1, description="Maximum tool calling iterations")
    enable_memory: bool = Field(default=True, description="Enable conversation memory")
    memory_window: int = Field(default=10, ge=1, description="Number of messages in memory")
    tools: List[str] = Field(default_factory=list, description="Available tool names")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Agent(BaseModel):
    """Base agent class.

    An agent is an autonomous entity that can:
    - Process user inputs
    - Reason about the task
    - Select and use appropriate tools
    - Maintain conversation memory
    - Coordinate with other agents (in multi-agent workflows)

    Example:
        ```python
        from unify_llm.agent import Agent, AgentConfig
        from unify_llm import UnifyLLM

        # Create LLM client
        client = UnifyLLM(provider="openai", api_key="sk-...")

        # Configure agent
        config = AgentConfig(
            name="assistant",
            model="gpt-4",
            provider="openai",
            system_prompt="You are a helpful assistant with access to tools.",
            tools=["search_web", "send_email"]
        )

        # Create agent
        agent = Agent(config=config, client=client)
        ```
    """

    config: AgentConfig = Field(..., description="Agent configuration")
    client: Any = Field(..., description="UnifyLLM client instance")

    class Config:
        arbitrary_types_allowed = True

    def get_system_message(self) -> Dict[str, str]:
        """Get the system message for the agent.

        Returns:
            System message dict
        """
        return {
            "role": "system",
            "content": self.config.system_prompt
        }

    def format_tool_description(self, tool: "Tool") -> str:
        """Format a tool description for the LLM.

        Args:
            tool: Tool to format

        Returns:
            Formatted tool description
        """
        params_desc = "\n".join([
            f"  - {name}: {param.get('description', 'No description')} ({param.get('type', 'any')})"
            for name, param in tool.parameters.items()
        ])

        return f"""
Tool: {tool.name}
Description: {tool.description}
Parameters:
{params_desc}
""".strip()

    def should_continue_iteration(self, iteration: int, response: Any) -> bool:
        """Determine if agent should continue iterating.

        Args:
            iteration: Current iteration number
            response: Latest LLM response

        Returns:
            True if should continue, False otherwise
        """
        if iteration >= self.config.max_iterations:
            return False

        # Check if response contains tool calls
        if hasattr(response, 'choices') and response.choices:
            choice = response.choices[0]
            if hasattr(choice, 'message'):
                message = choice.message
                # Check for tool_calls in the message
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    return True

        return False
