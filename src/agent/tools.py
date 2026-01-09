"""Tool definitions and registry for AI agents."""

import inspect
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ToolParameterType(str, Enum):
    """Types for tool parameters."""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


class ToolParameter(BaseModel):
    """Definition of a tool parameter.

    Attributes:
        type: Parameter type
        description: Human-readable description
        required: Whether the parameter is required
        enum: Valid values (for enum parameters)
        default: Default value
    """

    type: ToolParameterType = Field(..., description="Parameter type")
    description: str = Field(default="", description="Parameter description")
    required: bool = Field(default=True, description="Whether required")
    enum: Optional[List[Any]] = Field(default=None, description="Valid enum values")
    default: Optional[Any] = Field(default=None, description="Default value")


class ToolResult(BaseModel):
    """Result from tool execution.

    Attributes:
        success: Whether tool execution succeeded
        output: Tool output data
        error: Error message if failed
        metadata: Additional metadata
    """

    success: bool = Field(..., description="Execution success status")
    output: Any = Field(default=None, description="Tool output")
    error: Optional[str] = Field(default=None, description="Error message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Tool(BaseModel):
    """Tool definition for AI agents.

    A tool is a function that an agent can call to perform actions or retrieve information.

    Example:
        ```python
        from src.agent import Tool, ToolParameter, ToolParameterType, ToolResult

        # Define a search tool
        def search_web(query: str, num_results: int = 5) -> ToolResult:
            # Implementation here
            results = perform_search(query, num_results)
            return ToolResult(success=True, output=results)

        # Register as a tool
        search_tool = Tool(
            name="search_web",
            description="Search the web for information",
            parameters={
                "query": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Search query",
                    required=True
                ),
                "num_results": ToolParameter(
                    type=ToolParameterType.INTEGER,
                    description="Number of results to return",
                    required=False,
                    default=5
                )
            },
            function=search_web
        )
        ```
    """

    name: str = Field(..., description="Unique tool name")
    description: str = Field(..., description="Tool description for LLM")
    parameters: Dict[str, Union[ToolParameter, Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Tool parameters"
    )
    function: Optional[Callable] = Field(default=None, description="Actual function to execute")
    async_function: Optional[Callable] = Field(
        default=None,
        description="Async version of the function"
    )

    class Config:
        arbitrary_types_allowed = True

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function calling format.

        Returns:
            Tool in OpenAI format
        """
        properties = {}
        required = []

        for param_name, param in self.parameters.items():
            if isinstance(param, dict):
                param_dict = param
            else:
                param_dict = param.model_dump()

            properties[param_name] = {
                "type": param_dict.get("type", "string"),
                "description": param_dict.get("description", "")
            }

            if param_dict.get("enum"):
                properties[param_name]["enum"] = param_dict["enum"]

            if param_dict.get("required", True):
                required.append(param_name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convert tool to Anthropic tool format.

        Returns:
            Tool in Anthropic format
        """
        input_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for param_name, param in self.parameters.items():
            if isinstance(param, dict):
                param_dict = param
            else:
                param_dict = param.model_dump()

            input_schema["properties"][param_name] = {
                "type": param_dict.get("type", "string"),
                "description": param_dict.get("description", "")
            }

            if param_dict.get("required", True):
                input_schema["required"].append(param_name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": input_schema
        }

    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool synchronously.

        Args:
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        if not self.function:
            return ToolResult(
                success=False,
                error=f"Tool '{self.name}' has no function defined"
            )

        try:
            result = self.function(**kwargs)
            if isinstance(result, ToolResult):
                return result
            else:
                return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error executing tool '{self.name}': {str(e)}"
            )

    async def aexecute(self, **kwargs) -> ToolResult:
        """Execute the tool asynchronously.

        Args:
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        if self.async_function:
            try:
                result = await self.async_function(**kwargs)
                if isinstance(result, ToolResult):
                    return result
                else:
                    return ToolResult(success=True, output=result)
            except Exception as e:
                return ToolResult(
                    success=False,
                    error=f"Error executing async tool '{self.name}': {str(e)}"
                )
        elif self.function:
            # Fall back to sync execution
            return self.execute(**kwargs)
        else:
            return ToolResult(
                success=False,
                error=f"Tool '{self.name}' has no function defined"
            )


class ToolRegistry:
    """Registry for managing tools.

    Example:
        ```python
        from src.agent import ToolRegistry, Tool

        registry = ToolRegistry()

        # Register a tool
        registry.register(search_tool)

        # Get a tool
        tool = registry.get("search_web")

        # List all tools
        all_tools = registry.list_tools()

        # Get tools in OpenAI format
        openai_tools = registry.get_tools_for_provider("openai")
        ```
    """

    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool.

        Args:
            tool: Tool to register
        """
        self._tools[tool.name] = tool

    def register_function(
            self,
            name: str,
            description: str,
            function: Callable,
            parameters: Optional[Dict[str, Union[ToolParameter, Dict[str, Any]]]] = None,
            async_function: Optional[Callable] = None
    ) -> Tool:
        """Register a function as a tool.

        Args:
            name: Tool name
            description: Tool description
            function: Function to execute
            parameters: Tool parameters (auto-detected if None)
            async_function: Async version of function

        Returns:
            Registered tool
        """
        if parameters is None:
            # Auto-detect parameters from function signature
            parameters = self._auto_detect_parameters(function)

        tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            function=function,
            async_function=async_function
        )

        self.register(tool)
        return tool

    def _auto_detect_parameters(self, func: Callable) -> Dict[str, ToolParameter]:
        """Auto-detect parameters from function signature.

        Args:
            func: Function to inspect

        Returns:
            Detected parameters
        """
        sig = inspect.signature(func)
        parameters = {}

        type_mapping = {
            str: ToolParameterType.STRING,
            int: ToolParameterType.INTEGER,
            float: ToolParameterType.NUMBER,
            bool: ToolParameterType.BOOLEAN,
            dict: ToolParameterType.OBJECT,
            list: ToolParameterType.ARRAY
        }

        for param_name, param in sig.parameters.items():
            param_type = type_mapping.get(param.annotation, ToolParameterType.STRING)
            has_default = param.default != inspect.Parameter.empty

            parameters[param_name] = ToolParameter(
                type=param_type,
                description=f"Parameter {param_name}",
                required=not has_default,
                default=param.default if has_default else None
            )

        return parameters

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        """List all registered tools.

        Returns:
            List of all tools
        """
        return list(self._tools.values())

    def get_tools_for_provider(self, provider: str) -> List[Dict[str, Any]]:
        """Get tools in provider-specific format.

        Args:
            provider: Provider name (openai, anthropic, etc.)

        Returns:
            Tools in provider format
        """
        tools = []
        for tool in self._tools.values():
            if provider in ["openai", "openrouter", "grok", "databricks"]:
                tools.append(tool.to_openai_format())
            elif provider in ["anthropic", "anthropic_openai"]:
                tools.append(tool.to_anthropic_format())
            else:
                # Default to OpenAI format
                tools.append(tool.to_openai_format())
        return tools

    def unregister(self, name: str) -> bool:
        """Unregister a tool.

        Args:
            name: Tool name to unregister

        Returns:
            True if unregistered, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
