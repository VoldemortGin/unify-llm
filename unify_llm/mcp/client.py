"""MCP Client implementation."""


from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from unify_llm.mcp.protocol import (
    ClientCapabilities,
    InitializeParams,
    InitializeResult,
    MCPRequest,
    PromptDefinition,
    ResourceDefinition,
    ToolDefinition,
)
from unify_llm.mcp.transport import MCPTransport


class MCPClientConfig(BaseModel):
    """Configuration for MCP client."""
    client_name: str = "unify-llm"
    client_version: str = "0.1.0"
    protocol_version: str = "2024-11-05"
    capabilities: dict[str, Any] | None = None


class MCPClient:
    """MCP Client for connecting to MCP servers.

    This client can connect to MCP servers to access tools, resources,
    and prompts exposed by the server.

    Example:
        ```python
        from unify_llm.mcp import MCPClient, MCPClientConfig, StdioTransport

        # Create client
        config = MCPClientConfig(client_name="my-app")
        transport = StdioTransport()
        client = MCPClient(config, transport)

        # Connect and initialize
        await client.connect()
        await client.initialize()

        # List available tools
        tools = await client.list_tools()

        # Call a tool
        result = await client.call_tool("calculator", {"expression": "2+2"})

        # Close connection
        await client.close()
        ```
    """

    def __init__(self, config: MCPClientConfig, transport: MCPTransport):
        """Initialize MCP client.

        Args:
            config: Client configuration
            transport: Transport layer (stdio, SSE, WebSocket)
        """
        self.config = config
        self.transport = transport
        self._request_id = 0
        self._pending_requests: dict[int, asyncio.Future] = {}
        self._server_capabilities: dict[str, Any] | None = None
        self._connected = False
        self._receive_task: asyncio.Task | None = None

    async def connect(self) -> None:
        """Connect to the MCP server."""
        await self.transport.connect()
        self._connected = True

        # Start receiving messages
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def initialize(self) -> InitializeResult:
        """Initialize the MCP session with the server.

        Returns:
            Server initialization result with capabilities
        """
        params = InitializeParams(
            protocol_version=self.config.protocol_version,
            capabilities=ClientCapabilities(
                **(self.config.capabilities or {})
            ),
            client_info={
                "name": self.config.client_name,
                "version": self.config.client_version,
            }
        )

        response = await self._send_request("initialize", params.model_dump())
        result = InitializeResult(**response)
        self._server_capabilities = result.capabilities.model_dump()

        # Send initialized notification
        await self._send_notification("notifications/initialized")

        return result

    async def list_tools(self) -> list[ToolDefinition]:
        """List all tools available on the server.

        Returns:
            List of tool definitions
        """
        response = await self._send_request("tools/list")
        return [ToolDefinition(**tool) for tool in response.get("tools", [])]

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a tool on the server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        params = {
            "name": tool_name,
            "arguments": arguments
        }
        return await self._send_request("tools/call", params)

    async def list_resources(self) -> list[ResourceDefinition]:
        """List all resources available on the server.

        Returns:
            List of resource definitions
        """
        response = await self._send_request("resources/list")
        return [ResourceDefinition(**r) for r in response.get("resources", [])]

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource from the server.

        Args:
            uri: Resource URI

        Returns:
            Resource contents
        """
        params = {"uri": uri}
        return await self._send_request("resources/read", params)

    async def list_prompts(self) -> list[PromptDefinition]:
        """List all prompts available on the server.

        Returns:
            List of prompt definitions
        """
        response = await self._send_request("prompts/list")
        return [PromptDefinition(**p) for p in response.get("prompts", [])]

    async def get_prompt(
        self,
        prompt_name: str,
        arguments: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Get a prompt from the server.

        Args:
            prompt_name: Name of the prompt
            arguments: Prompt arguments

        Returns:
            Prompt with interpolated arguments
        """
        params = {
            "name": prompt_name,
            "arguments": arguments or {}
        }
        return await self._send_request("prompts/get", params)

    async def close(self) -> None:
        """Close the MCP connection."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        await self.transport.close()
        self._connected = False

    async def _send_request(
        self,
        method: str,
        params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send a request and wait for response.

        Args:
            method: RPC method name
            params: Request parameters

        Returns:
            Response result

        Raises:
            Exception if response contains an error
        """
        request_id = self._get_next_id()
        future = asyncio.Future()
        self._pending_requests[request_id] = future

        request = MCPRequest(
            id=request_id,
            method=method,
            params=params
        )

        await self.transport.send(request.model_dump(exclude_none=True))

        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            if "error" in response:
                raise Exception(f"MCP Error: {response['error']}")
            return response.get("result", {})
        finally:
            self._pending_requests.pop(request_id, None)

    async def _send_notification(
        self,
        method: str,
        params: dict[str, Any] | None = None
    ) -> None:
        """Send a notification (no response expected).

        Args:
            method: Notification method name
            params: Notification parameters
        """
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        await self.transport.send(notification)

    async def _receive_loop(self) -> None:
        """Continuously receive messages from the transport."""
        try:
            while self._connected:
                message = await self.transport.receive()
                await self._handle_message(message)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in receive loop: {e}")

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Handle an incoming message.

        Args:
            message: Received message
        """
        if "id" in message and message["id"] in self._pending_requests:
            # This is a response to a pending request
            future = self._pending_requests.get(message["id"])
            if future and not future.done():
                future.set_result(message)
        elif "method" in message:
            # This is a notification or request from server
            # Handle server-initiated requests here if needed
            pass

    def _get_next_id(self) -> int:
        """Get next request ID.

        Returns:
            Request ID
        """
        self._request_id += 1
        return self._request_id
