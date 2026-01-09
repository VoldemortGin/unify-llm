"""Agent executor for running AI agents with tool calling support."""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from src.agent.base import Agent
from src.agent.memory import ConversationMemory
from src.agent.tools import ToolRegistry, ToolResult

logger = logging.getLogger(__name__)


def _get_tool_call_attr(tc: Union[Dict, Any], attr: str) -> Any:
    """Get attribute from tool_call, handling both dict and object formats.

    Args:
        tc: Tool call (dict or object)
        attr: Attribute name (supports nested like 'function.name')

    Returns:
        The attribute value
    """
    parts = attr.split('.')
    value = tc
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = getattr(value, part, None)
    return value


class ExecutionResult(BaseModel):
    """Result from agent execution.

    Attributes:
        success: Whether execution succeeded
        output: Final output from the agent
        iterations: Number of iterations performed
        tool_calls: List of tool calls made
        error: Error message if failed
        metadata: Additional metadata
    """

    success: bool = Field(..., description="Execution success status")
    output: str = Field(default="", description="Final agent output")
    iterations: int = Field(default=0, description="Number of iterations")
    tool_calls: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Tool calls made"
    )
    error: Optional[str] = Field(default=None, description="Error message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AgentExecutor:
    """Executes AI agents with tool calling support.

    The executor handles:
    - Running the agent's reasoning loop
    - Tool selection and execution
    - Memory management
    - Error handling and retries

    Example:
        ```python
        from src import UnifyLLM
        from src.agent import (
            Agent, AgentConfig, AgentExecutor,
            ToolRegistry, ConversationMemory
        )

        # Initialize client
        client = UnifyLLM(provider="openai", api_key="sk-...")

        # Create agent
        config = AgentConfig(
            name="assistant",
            model="gpt-4",
            provider="openai",
            tools=["search_web", "calculate"]
        )
        agent = Agent(config=config, client=client)

        # Create tool registry and register tools
        registry = ToolRegistry()
        # ... register tools ...

        # Create executor
        executor = AgentExecutor(
            agent=agent,
            tool_registry=registry,
            memory=ConversationMemory(window_size=10)
        )

        # Run agent
        result = executor.run("What's 15 * 23?")
        print(result.output)
        ```
    """

    def __init__(
            self,
            agent: Agent,
            tool_registry: Optional[ToolRegistry] = None,
            memory: Optional[ConversationMemory] = None,
            verbose: bool = False
    ):
        """Initialize the agent executor.

        Args:
            agent: Agent to execute
            tool_registry: Tool registry with available tools
            memory: Conversation memory (creates new if None)
            verbose: Whether to log execution details
        """
        self.agent = agent
        self.tool_registry = tool_registry or ToolRegistry()
        self.memory = memory or ConversationMemory(
            window_size=agent.config.memory_window
        )
        self.verbose = verbose

        # Add system message to memory if enabled
        if agent.config.enable_memory:
            self.memory.add_system_message(agent.config.system_prompt)

    def run(self, user_input: str, **kwargs) -> ExecutionResult:
        """Run the agent synchronously.

        Args:
            user_input: User input message
            **kwargs: Additional parameters for LLM

        Returns:
            Execution result
        """
        try:
            # Add user message to memory
            if self.agent.config.enable_memory:
                self.memory.add_user_message(user_input)

            # Get tools in the right format for the provider
            tools = None
            if self.agent.config.tools:
                tools = self.tool_registry.get_tools_for_provider(
                    self.agent.config.provider
                )

            # Prepare messages
            messages = self.memory.get_messages() if self.agent.config.enable_memory else [
                self.agent.get_system_message(),
                {"role": "user", "content": user_input}
            ]

            iteration = 0
            tool_calls_log = []

            # Agent reasoning loop
            while iteration < self.agent.config.max_iterations:
                iteration += 1

                if self.verbose:
                    logger.info(f"Iteration {iteration}/{self.agent.config.max_iterations}")

                # Call LLM
                response = self.agent.client.chat(
                    model=self.agent.config.model,
                    messages=messages,
                    temperature=self.agent.config.temperature,
                    max_tokens=self.agent.config.max_tokens,
                    tools=tools,
                    **kwargs
                )

                # Extract assistant message
                assistant_message = response.choices[0].message

                # Check for tool calls
                tool_calls = getattr(assistant_message, 'tool_calls', None)

                if not tool_calls:
                    # No tool calls, we have final answer
                    content = getattr(assistant_message, 'content', '')
                    if self.agent.config.enable_memory:
                        self.memory.add_assistant_message(content)

                    return ExecutionResult(
                        success=True,
                        output=content,
                        iterations=iteration,
                        tool_calls=tool_calls_log,
                        metadata={
                            "finish_reason": response.choices[0].finish_reason,
                            "model": response.model
                        }
                    )

                # Process tool calls
                if self.verbose:
                    logger.info(f"Processing {len(tool_calls)} tool calls")

                # Add assistant message with tool calls to messages
                messages.append({
                    "role": "assistant",
                    "content": getattr(assistant_message, 'content', None),
                    "tool_calls": [
                        {
                            "id": _get_tool_call_attr(tc, 'id'),
                            "type": _get_tool_call_attr(tc, 'type') or "function",
                            "function": {
                                "name": _get_tool_call_attr(tc, 'function.name'),
                                "arguments": _get_tool_call_attr(tc, 'function.arguments')
                            }
                        }
                        for tc in tool_calls
                    ]
                })

                # Execute tools
                for tool_call in tool_calls:
                    tool_name = _get_tool_call_attr(tool_call, 'function.name')
                    tool_args = json.loads(_get_tool_call_attr(tool_call, 'function.arguments'))

                    if self.verbose:
                        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                    # Get tool from registry
                    tool = self.tool_registry.get(tool_name)

                    if not tool:
                        tool_result = ToolResult(
                            success=False,
                            error=f"Tool '{tool_name}' not found in registry"
                        )
                    else:
                        # Execute tool
                        tool_result = tool.execute(**tool_args)

                    # Log tool call
                    tool_calls_log.append({
                        "tool": tool_name,
                        "arguments": tool_args,
                        "result": tool_result.model_dump()
                    })

                    # Add tool result to messages
                    result_content = json.dumps({
                        "success": tool_result.success,
                        "output": tool_result.output,
                        "error": tool_result.error
                    })

                    messages.append({
                        "role": "tool",
                        "tool_call_id": _get_tool_call_attr(tool_call, 'id'),
                        "name": tool_name,
                        "content": result_content
                    })

                    if self.agent.config.enable_memory:
                        self.memory.add_tool_message(
                            content=result_content,
                            name=tool_name,
                            tool_call_id=_get_tool_call_attr(tool_call, 'id')
                        )

            # Max iterations reached
            return ExecutionResult(
                success=False,
                output="",
                iterations=iteration,
                tool_calls=tool_calls_log,
                error=f"Maximum iterations ({self.agent.config.max_iterations}) reached"
            )

        except Exception as e:
            logger.error(f"Error executing agent: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                output="",
                iterations=iteration if 'iteration' in locals() else 0,
                tool_calls=tool_calls_log if 'tool_calls_log' in locals() else [],
                error=str(e)
            )

    async def arun(self, user_input: str, **kwargs) -> ExecutionResult:
        """Run the agent asynchronously.

        Args:
            user_input: User input message
            **kwargs: Additional parameters for LLM

        Returns:
            Execution result
        """
        try:
            # Add user message to memory
            if self.agent.config.enable_memory:
                self.memory.add_user_message(user_input)

            # Get tools in the right format for the provider
            tools = None
            if self.agent.config.tools:
                tools = self.tool_registry.get_tools_for_provider(
                    self.agent.config.provider
                )

            # Prepare messages
            messages = self.memory.get_messages() if self.agent.config.enable_memory else [
                self.agent.get_system_message(),
                {"role": "user", "content": user_input}
            ]

            iteration = 0
            tool_calls_log = []

            # Agent reasoning loop
            while iteration < self.agent.config.max_iterations:
                iteration += 1

                if self.verbose:
                    logger.info(f"Iteration {iteration}/{self.agent.config.max_iterations}")

                # Call LLM
                response = await self.agent.client.achat(
                    model=self.agent.config.model,
                    messages=messages,
                    temperature=self.agent.config.temperature,
                    max_tokens=self.agent.config.max_tokens,
                    tools=tools,
                    **kwargs
                )

                # Extract assistant message
                assistant_message = response.choices[0].message

                # Check for tool calls
                tool_calls = getattr(assistant_message, 'tool_calls', None)

                if not tool_calls:
                    # No tool calls, we have final answer
                    content = getattr(assistant_message, 'content', '')
                    if self.agent.config.enable_memory:
                        self.memory.add_assistant_message(content)

                    return ExecutionResult(
                        success=True,
                        output=content,
                        iterations=iteration,
                        tool_calls=tool_calls_log,
                        metadata={
                            "finish_reason": response.choices[0].finish_reason,
                            "model": response.model
                        }
                    )

                # Process tool calls
                if self.verbose:
                    logger.info(f"Processing {len(tool_calls)} tool calls")

                # Add assistant message with tool calls to messages
                messages.append({
                    "role": "assistant",
                    "content": getattr(assistant_message, 'content', None),
                    "tool_calls": [
                        {
                            "id": _get_tool_call_attr(tc, 'id'),
                            "type": _get_tool_call_attr(tc, 'type') or "function",
                            "function": {
                                "name": _get_tool_call_attr(tc, 'function.name'),
                                "arguments": _get_tool_call_attr(tc, 'function.arguments')
                            }
                        }
                        for tc in tool_calls
                    ]
                })

                # Execute tools
                for tool_call in tool_calls:
                    tool_name = _get_tool_call_attr(tool_call, 'function.name')
                    tool_args = json.loads(_get_tool_call_attr(tool_call, 'function.arguments'))

                    if self.verbose:
                        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                    # Get tool from registry
                    tool = self.tool_registry.get(tool_name)

                    if not tool:
                        tool_result = ToolResult(
                            success=False,
                            error=f"Tool '{tool_name}' not found in registry"
                        )
                    else:
                        # Execute tool asynchronously
                        tool_result = await tool.aexecute(**tool_args)

                    # Log tool call
                    tool_calls_log.append({
                        "tool": tool_name,
                        "arguments": tool_args,
                        "result": tool_result.model_dump()
                    })

                    # Add tool result to messages
                    result_content = json.dumps({
                        "success": tool_result.success,
                        "output": tool_result.output,
                        "error": tool_result.error
                    })

                    messages.append({
                        "role": "tool",
                        "tool_call_id": _get_tool_call_attr(tool_call, 'id'),
                        "name": tool_name,
                        "content": result_content
                    })

                    if self.agent.config.enable_memory:
                        self.memory.add_tool_message(
                            content=result_content,
                            name=tool_name,
                            tool_call_id=_get_tool_call_attr(tool_call, 'id')
                        )

            # Max iterations reached
            return ExecutionResult(
                success=False,
                output="",
                iterations=iteration,
                tool_calls=tool_calls_log,
                error=f"Maximum iterations ({self.agent.config.max_iterations}) reached"
            )

        except Exception as e:
            logger.error(f"Error executing agent: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                output="",
                iterations=iteration if 'iteration' in locals() else 0,
                tool_calls=tool_calls_log if 'tool_calls_log' in locals() else [],
                error=str(e)
            )

    def reset_memory(self) -> None:
        """Reset the conversation memory."""
        self.memory.clear()
        if self.agent.config.enable_memory:
            self.memory.add_system_message(self.agent.config.system_prompt)
