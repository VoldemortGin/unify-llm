"""
Example: Using MCP Client with A2A Agents

This example demonstrates how to integrate MCP clients with A2A agents,
allowing agents to use tools exposed by MCP servers.
"""

import asyncio
import os
from unify_llm import UnifyLLM
from unify_llm.agent import Agent, AgentConfig, AgentType
from unify_llm.mcp import MCPClient, MCPClientConfig, StdioTransport
from unify_llm.a2a import A2AAgent, A2AAgentConfig, AgentCapability, AgentRegistry


class MCPIntegratedAgent:
    """Agent that can use MCP tools.

    This class wraps a standard agent and allows it to call
    tools from an MCP server.

    Example:
        ```python
        agent = MCPIntegratedAgent(base_agent, mcp_client)
        result = await agent.call_mcp_tool("calculator", {"expression": "2+2"})
        ```
    """

    def __init__(self, base_agent: Agent, mcp_client: MCPClient):
        """Initialize MCP-integrated agent.

        Args:
            base_agent: Base agent
            mcp_client: Connected MCP client
        """
        self.base_agent = base_agent
        self.mcp_client = mcp_client
        self._available_tools = {}

    async def initialize(self) -> None:
        """Initialize and discover MCP tools."""
        # List available tools from MCP server
        tools = await self.mcp_client.list_tools()
        for tool in tools:
            self._available_tools[tool.name] = tool

        print(f"✅ Discovered {len(self._available_tools)} MCP tools:")
        for name in self._available_tools:
            print(f"   - {name}")

    async def call_mcp_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call an MCP tool.

        Args:
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        if tool_name not in self._available_tools:
            raise ValueError(f"Tool not found: {tool_name}")

        result = await self.mcp_client.call_tool(tool_name, arguments)
        return result

    async def execute_with_mcp(self, task: str) -> str:
        """Execute a task that may require MCP tools.

        Args:
            task: Task description

        Returns:
            Task result
        """
        # Agent can analyze task and decide which MCP tools to use
        # For now, this is a simplified version
        return f"Executed task with MCP tools available: {task}"


async def example_mcp_with_a2a():
    """Example: Integrate MCP client with A2A agent."""
    print("\n" + "=" * 60)
    print("Example: MCP Client + A2A Agent Integration")
    print("=" * 60)

    # Note: This example assumes you have an MCP server running
    # You can start one with: python examples/mcp_server_filesystem.py

    # Step 1: Connect to MCP server
    print("\n📡 Connecting to MCP server...")
    mcp_config = MCPClientConfig(client_name="integrated-agent")
    mcp_transport = StdioTransport()
    mcp_client = MCPClient(mcp_config, mcp_transport)

    # In production, you would:
    # await mcp_client.connect()
    # await mcp_client.initialize()

    print("✅ (Simulated) MCP client ready")

    # Step 2: Create base agent with Databricks
    api_key = os.getenv("DATABRICKS_API_KEY", "demo-key")
    base_url = os.getenv("DATABRICKS_BASE_URL", "https://demo.databricks.com")

    if api_key == "demo-key":
        print("\n⚠️  Demo mode: Set DATABRICKS_API_KEY for real testing")

    print("\n📦 Creating AI agent...")
    client = UnifyLLM(provider="databricks", api_key=api_key, base_url=base_url)
    base_agent = Agent(
        config=AgentConfig(
            name="mcp_enabled_agent",
            agent_type=AgentType.TOOLS,
            model="claude-opus-4-5",
            provider="databricks",
            system_prompt="You are an agent with access to MCP tools.",
            max_iterations=3
        ),
        client=client
    )

    # Step 3: Create MCP-integrated agent
    mcp_agent = MCPIntegratedAgent(base_agent, mcp_client)
    # await mcp_agent.initialize()  # Would discover MCP tools

    print("✅ MCP-integrated agent created")

    # Step 4: Wrap with A2A capabilities
    print("\n🤝 Adding A2A capabilities...")
    registry = AgentRegistry()

    a2a_agent = A2AAgent(
        base_agent=base_agent,
        config=A2AAgentConfig(
            agent_name="mcp_a2a_agent",
            capabilities=[
                AgentCapability(
                    name="execute_with_tools",
                    description="Execute tasks using MCP tools",
                    input_schema={"type": "object", "properties": {"task": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
                    tags=["mcp", "tools"]
                )
            ]
        ),
        registry=registry
    )

    # Register capability handler that uses MCP tools
    @a2a_agent.handle_capability("execute_with_tools")
    async def handle_task_with_mcp(input_data):
        task = input_data.get("task", "")
        # Use MCP tools to execute task
        # result = await mcp_agent.execute_with_mcp(task)
        result = f"Executed '{task}' using MCP tools (simulated)"
        return {"result": result}

    await a2a_agent.start()
    print("✅ A2A agent started with MCP integration")

    # Step 5: Demonstrate usage
    print("\n🚀 Demonstrating MCP + A2A integration...")

    # Simulate calling MCP tool
    print("\n   Example 1: Direct MCP tool call")
    # result = await mcp_agent.call_mcp_tool("calculator", {"expression": "10 * 5"})
    print("   Result: 50 (simulated)")

    # Simulate A2A task delegation with MCP
    print("\n   Example 2: A2A task with MCP tools")
    result = await a2a_agent.handle_request(
        type("Request", (), {
            "id": "test",
            "sender_id": "user",
            "method": "execute_task",
            "params": {
                "task_id": "calc",
                "capability": "execute_with_tools",
                "input_data": {"task": "Calculate 15 * 23"}
            }
        })()
    )
    print(f"   Result: {result}")

    # Cleanup
    await a2a_agent.stop()
    # await mcp_client.close()
    print("\n✅ Example complete")


async def example_multi_mcp_servers():
    """Example: Agent using multiple MCP servers."""
    print("\n" + "=" * 60)
    print("Example: Agent with Multiple MCP Servers")
    print("=" * 60)

    print("\n💡 Concept: An agent can connect to multiple MCP servers:")
    print("   - Filesystem server: File operations")
    print("   - Database server: Data queries")
    print("   - API server: External API calls")
    print("\nEach server exposes different tools, and the agent can use all of them!")

    print("\n📋 Example configuration:")
    print("""
    # Connect to multiple MCP servers
    fs_client = MCPClient(config1, transport1)
    db_client = MCPClient(config2, transport2)
    api_client = MCPClient(config3, transport3)

    # Initialize all
    await fs_client.connect()
    await db_client.connect()
    await api_client.connect()

    # Agent can now use tools from all servers
    files = await fs_client.call_tool("list_directory", {"path": "."})
    data = await db_client.call_tool("query", {"sql": "SELECT * FROM users"})
    result = await api_client.call_tool("http_request", {"url": "..."})
    """)


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("🔌 MCP Client Integration Examples")
    print("=" * 60)

    await example_mcp_with_a2a()
    await example_multi_mcp_servers()

    print("\n" + "=" * 60)
    print("✅ All examples complete!")
    print("=" * 60)
    print("\n📚 For production use:")
    print("   1. Start an MCP server (examples/mcp_server_filesystem.py)")
    print("   2. Connect your agent to the server")
    print("   3. Discover and use available tools")
    print("   4. Combine with A2A for multi-agent collaboration")


if __name__ == "__main__":
    asyncio.run(main())
