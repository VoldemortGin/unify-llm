"""MCP Server implementation."""


from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel

from unify_llm.mcp.protocol import (
    InitializeResult,
    MCPResponse,
    PromptDefinition,
    ResourceDefinition,
    ServerCapabilities,
    ToolDefinition,
)
from unify_llm.mcp.transport import MCPTransport


class MCPServerConfig(BaseModel):
    """Configuration for MCP server."""
    server_name: str = "unify-llm-server"
    server_version: str = "0.1.0"
    protocol_version: str = "2024-11-05"
    capabilities: dict[str, Any] | None = None


class MCPServer:
    """MCP Server for exposing tools, resources, and prompts.

    This server allows AI agents to expose their capabilities via the MCP protocol,
    enabling other agents or applications to discover and use them.

    Example:
        ```python
        from unify_llm.mcp import MCPServer, MCPServerConfig, StdioTransport

        # Create server
        config = MCPServerConfig(server_name="my-agent")
        server = MCPServer(config)

        # Register a tool
        @server.tool("calculator", "Perform mathematical calculations")
        async def calculator(a: int, b: int, operation: str) -> dict[str, Any]:
            # SECURITY: Never use eval() - use explicit operations instead
            if operation == "add":
                return {"result": a + b}
            elif operation == "subtract":
                return {"result": a - b}
            elif operation == "multiply":
                return {"result": a * b}
            elif operation == "divide":
                return {"result": a / b if b != 0 else "error: division by zero"}
            else:
                return {"error": f"Unknown operation: {operation}"}

        # Register a resource
        @server.resource("file://data.txt", "text/plain", "Sample data file")
        async def get_data() -> str:
            return "Hello, World!"

        # Start server
        transport = StdioTransport()
        await server.start(transport)
        ```
    """

    def __init__(self, config: MCPServerConfig):
        """Initialize MCP server.

        Args:
            config: Server configuration
        """
        self.config = config
        self.transport: MCPTransport | None = None
        self._tools: dict[str, dict[str, Any]] = {}
        self._resources: dict[str, dict[str, Any]] = {}
        self._prompts: dict[str, dict[str, Any]] = {}
        self._initialized = False
        self._running = False

    def tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any] | None = None
    ):
        """Decorator to register a tool.

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON Schema for tool parameters

        Example:
            ```python
            @server.tool("add", "Add two numbers")
            async def add(a: int, b: int) -> dict[str, Any]:
                return {"result": a + b}
            ```
        """
        def decorator(func: Callable):
            # Auto-generate schema from function signature if not provided
            if input_schema is None:
                import inspect
                sig = inspect.signature(func)
                properties = {}
                required = []

                for param_name, param in sig.parameters.items():
                    param_type = "string"  # default
                    if param.annotation != inspect.Parameter.empty:
                        if param.annotation is int:
                            param_type = "integer"
                        elif param.annotation is float:
                            param_type = "number"
                        elif param.annotation is bool:
                            param_type = "boolean"

                    properties[param_name] = {"type": param_type}
                    if param.default is inspect.Parameter.empty:
                        required.append(param_name)

                schema = {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            else:
                schema = input_schema

            self._tools[name] = {
                "definition": ToolDefinition(
                    name=name,
                    description=description,
                    input_schema=schema
                ),
                "handler": func
            }
            return func

        return decorator

    def resource(
        self,
        uri: str,
        mime_type: str,
        description: str,
        name: str | None = None
    ):
        """Decorator to register a resource.

        Args:
            uri: Resource URI
            mime_type: MIME type
            description: Resource description
            name: Resource name (defaults to URI)

        Example:
            ```python
            @server.resource("file://config.json", "application/json", "Configuration")
            async def get_config() -> str:
                return '{"key": "value"}'
            ```
        """
        def decorator(func: Callable):
            from unify_llm.mcp.protocol import ResourceType

            # Determine resource type from MIME type
            if mime_type.startswith("text/"):
                resource_type = ResourceType.TEXT
            elif mime_type.startswith("image/"):
                resource_type = ResourceType.IMAGE
            else:
                resource_type = ResourceType.BLOB

            self._resources[uri] = {
                "definition": ResourceDefinition(
                    uri=uri,
                    name=name or uri,
                    description=description,
                    mime_type=mime_type,
                    type=resource_type
                ),
                "handler": func
            }
            return func

        return decorator

    def prompt(
        self,
        name: str,
        description: str,
        arguments: Optional[list[dict[str, Any]]] = None
    ):
        """Decorator to register a prompt template.

        Args:
            name: Prompt name
            description: Prompt description
            arguments: Prompt arguments schema

        Example:
            ```python
            @server.prompt("greeting", "Generate a greeting message")
            async def greeting_prompt(name: str) -> dict[str, Any]:
                return {
                    "messages": [
                        {"role": "user", "content": f"Say hello to {name}"}
                    ]
                }
            ```
        """
        def decorator(func: Callable):
            self._prompts[name] = {
                "definition": PromptDefinition(
                    name=name,
                    description=description,
                    arguments=arguments or []
                ),
                "handler": func
            }
            return func

        return decorator

    async def start(self, transport: MCPTransport) -> None:
        """Start the MCP server.

        Args:
            transport: Transport layer to use
        """
        self.transport = transport
        await self.transport.connect()
        self._running = True

        # Process messages
        await self._message_loop()

    async def stop(self) -> None:
        """Stop the MCP server."""
        self._running = False
        if self.transport:
            await self.transport.close()

    async def _message_loop(self) -> None:
        """Main message processing loop."""
        while self._running:
            try:
                message = await self.transport.receive()
                await self._handle_message(message)
            except EOFError:
                break
            except Exception as e:
                print(f"Error processing message: {e}")

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Handle an incoming message.

        Args:
            message: Received message
        """
        method = message.get("method")
        msg_id = message.get("id")

        # Route to appropriate handler
        if method == "initialize":
            await self._handle_initialize(msg_id, message.get("params", {}))
        elif method == "tools/list":
            await self._handle_tools_list(msg_id)
        elif method == "tools/call":
            await self._handle_tool_call(msg_id, message.get("params", {}))
        elif method == "resources/list":
            await self._handle_resources_list(msg_id)
        elif method == "resources/read":
            await self._handle_resource_read(msg_id, message.get("params", {}))
        elif method == "prompts/list":
            await self._handle_prompts_list(msg_id)
        elif method == "prompts/get":
            await self._handle_prompt_get(msg_id, message.get("params", {}))
        elif method and method.startswith("notifications/"):
            # Handle notifications (no response needed)
            pass
        else:
            await self._send_error(msg_id, -32601, f"Method not found: {method}")

    async def _handle_initialize(self, msg_id: int, params: dict[str, Any]) -> None:
        """Handle initialization request."""
        self._initialized = True

        # Build capabilities
        capabilities = ServerCapabilities(
            tools={"listChanged": True} if self._tools else None,
            resources={"subscribe": True} if self._resources else None,
            prompts={"listChanged": True} if self._prompts else None,
        )

        result = InitializeResult(
            protocol_version=self.config.protocol_version,
            capabilities=capabilities,
            server_info={
                "name": self.config.server_name,
                "version": self.config.server_version
            }
        )

        await self._send_response(msg_id, result.model_dump())

    async def _handle_tools_list(self, msg_id: int) -> None:
        """Handle tools/list request."""
        tools = [t["definition"].model_dump() for t in self._tools.values()]
        await self._send_response(msg_id, {"tools": tools})

    async def _handle_tool_call(self, msg_id: int, params: dict[str, Any]) -> None:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self._tools:
            await self._send_error(msg_id, -32602, f"Tool not found: {tool_name}")
            return

        try:
            handler = self._tools[tool_name]["handler"]
            result = await handler(**arguments)
            await self._send_response(msg_id, {"content": [{"type": "text", "text": str(result)}]})
        except Exception as e:
            await self._send_error(msg_id, -32603, f"Tool execution error: {str(e)}")

    async def _handle_resources_list(self, msg_id: int) -> None:
        """Handle resources/list request."""
        resources = [r["definition"].model_dump() for r in self._resources.values()]
        await self._send_response(msg_id, {"resources": resources})

    async def _handle_resource_read(self, msg_id: int, params: dict[str, Any]) -> None:
        """Handle resources/read request."""
        uri = params.get("uri")

        if uri not in self._resources:
            await self._send_error(msg_id, -32602, f"Resource not found: {uri}")
            return

        try:
            handler = self._resources[uri]["handler"]
            content = await handler()
            resource_def = self._resources[uri]["definition"]

            await self._send_response(msg_id, {
                "contents": [{
                    "uri": uri,
                    "mimeType": resource_def.mime_type,
                    "text": content if isinstance(content, str) else str(content)
                }]
            })
        except Exception as e:
            await self._send_error(msg_id, -32603, f"Resource read error: {str(e)}")

    async def _handle_prompts_list(self, msg_id: int) -> None:
        """Handle prompts/list request."""
        prompts = [p["definition"].model_dump() for p in self._prompts.values()]
        await self._send_response(msg_id, {"prompts": prompts})

    async def _handle_prompt_get(self, msg_id: int, params: dict[str, Any]) -> None:
        """Handle prompts/get request."""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})

        if prompt_name not in self._prompts:
            await self._send_error(msg_id, -32602, f"Prompt not found: {prompt_name}")
            return

        try:
            handler = self._prompts[prompt_name]["handler"]
            result = await handler(**arguments)
            await self._send_response(msg_id, result)
        except Exception as e:
            await self._send_error(msg_id, -32603, f"Prompt error: {str(e)}")

    async def _send_response(self, msg_id: int, result: dict[str, Any]) -> None:
        """Send a response message."""
        response = MCPResponse(id=msg_id, result=result)
        await self.transport.send(response.model_dump(exclude_none=True))

    async def _send_error(
        self,
        msg_id: int,
        code: int,
        message: str
    ) -> None:
        """Send an error response."""
        response = MCPResponse(
            id=msg_id,
            error={"code": code, "message": message}
        )
        await self.transport.send(response.model_dump(exclude_none=True))
