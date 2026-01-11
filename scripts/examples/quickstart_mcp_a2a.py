"""
Quick Start: MCP & A2A with Databricks Claude Opus 4.5

This example demonstrates the basic usage of MCP and A2A protocols
with Databricks Claude Opus 4.5.

Run this after setting environment variables:
export DATABRICKS_API_KEY="dapi..."
export DATABRICKS_BASE_URL="https://your-workspace.cloud.databricks.com"
"""

import asyncio
import os
from unify_llm import UnifyLLM
from unify_llm.agent import Agent, AgentConfig, AgentType
from unify_llm.mcp import MCPServer, MCPServerConfig
from unify_llm.a2a import (
    A2AAgent,
    A2AAgentConfig,
    AgentCapability,
    AgentRegistry,
    AgentDiscovery,
    AgentCollaboration,
    CollaborationStrategy,
)


async def example_mcp_server():
    """Example 1: Create an MCP server that exposes agent tools"""
    print("\n" + "=" * 60)
    print("Example 1: MCP Server")
    print("=" * 60)

    # Create MCP server
    server = MCPServer(MCPServerConfig(
        server_name="example-agent-server",
        server_version="1.0.0"
    ))

    # Register a calculator tool
    @server.tool(
        name="calculator",
        description="Perform mathematical calculations",
        input_schema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        }
    )
    async def calculator(expression: str):
        try:
            result = eval(expression)
            return {"result": result, "expression": expression}
        except Exception as e:
            return {"error": str(e)}

    # Register a data resource
    @server.resource(
        uri="file://agent_status.json",
        mime_type="application/json",
        description="Current agent status"
    )
    async def get_status():
        return '{"status": "running", "uptime": "5m", "tasks_completed": 10}'

    # Register a prompt template
    @server.prompt(
        name="solve_problem",
        description="Generate a prompt for problem-solving",
        arguments=[
            {"name": "problem", "description": "Problem to solve", "required": True}
        ]
    )
    async def solve_prompt(problem: str):
        return {
            "messages": [
                {"role": "system", "content": "You are an expert problem solver."},
                {"role": "user", "content": f"Solve this problem: {problem}"}
            ]
        }

    print("✅ MCP Server created with:")
    print("   - Tool: calculator")
    print("   - Resource: agent_status.json")
    print("   - Prompt: solve_problem")
    print("\n💡 In production, you would start the server with:")
    print("   await server.start(transport)")


async def example_a2a_agents():
    """Example 2: Create A2A agents that can communicate"""
    print("\n" + "=" * 60)
    print("Example 2: A2A Agent Communication")
    print("=" * 60)

    # Get Databricks credentials
    api_key = os.getenv("DATABRICKS_API_KEY")
    base_url = os.getenv("DATABRICKS_BASE_URL")

    if not api_key or not base_url:
        print("⚠️  Set DATABRICKS_API_KEY and DATABRICKS_BASE_URL to run this example")
        return

    # Create shared registry
    registry = AgentRegistry()

    # Create first agent: Math Expert
    print("\n📦 Creating Math Expert agent...")
    client1 = UnifyLLM(provider="databricks", api_key=api_key, base_url=base_url)
    base_agent1 = Agent(
        config=AgentConfig(
            name="math_expert",
            agent_type=AgentType.TOOLS,
            model="claude-opus-4-5",  # or your endpoint name
            provider="databricks",
            system_prompt="You are a mathematics expert.",
            max_iterations=3
        ),
        client=client1
    )

    a2a_agent1 = A2AAgent(
        base_agent=base_agent1,
        config=A2AAgentConfig(
            agent_name="math_expert",
            capabilities=[
                AgentCapability(
                    name="solve_math",
                    description="Solve mathematical problems",
                    input_schema={
                        "type": "object",
                        "properties": {"problem": {"type": "string"}}
                    },
                    output_schema={
                        "type": "object",
                        "properties": {"solution": {"type": "string"}}
                    },
                    tags=["math", "calculation"]
                )
            ]
        ),
        registry=registry
    )

    # Register capability handler
    @a2a_agent1.handle_capability("solve_math")
    async def handle_math(input_data):
        problem = input_data.get("problem", "")
        print(f"   🔢 Solving: {problem}")
        return {"solution": f"Solution to '{problem}' (simulated)"}

    # Start agent
    await a2a_agent1.start()
    print(f"✅ Agent 1 started: {a2a_agent1.agent_id}")

    # Create second agent: Data Analyst
    print("\n📦 Creating Data Analyst agent...")
    client2 = UnifyLLM(provider="databricks", api_key=api_key, base_url=base_url)
    base_agent2 = Agent(
        config=AgentConfig(
            name="data_analyst",
            agent_type=AgentType.TOOLS,
            model="claude-opus-4-5",
            provider="databricks",
            system_prompt="You are a data analysis expert.",
            max_iterations=3
        ),
        client=client2
    )

    a2a_agent2 = A2AAgent(
        base_agent=base_agent2,
        config=A2AAgentConfig(
            agent_name="data_analyst",
            capabilities=[
                AgentCapability(
                    name="analyze_data",
                    description="Analyze datasets",
                    input_schema={
                        "type": "object",
                        "properties": {"data": {"type": "string"}}
                    },
                    output_schema={
                        "type": "object",
                        "properties": {"analysis": {"type": "string"}}
                    },
                    tags=["data", "analysis"]
                )
            ]
        ),
        registry=registry
    )

    await a2a_agent2.start()
    print(f"✅ Agent 2 started: {a2a_agent2.agent_id}")

    # Test agent discovery
    print("\n🔍 Testing agent discovery...")
    discovery = AgentDiscovery(registry)
    math_agents = await discovery.discover(capabilities=["solve_math"])
    print(f"✅ Found {len(math_agents)} agent(s) with 'solve_math' capability")

    # Test task delegation
    print("\n📤 Testing task delegation...")
    result = await a2a_agent2.delegate_task(
        target_agent_id=a2a_agent1.agent_id,
        capability="solve_math",
        input_data={"problem": "What is 15 * 23?"}
    )
    print(f"✅ Delegation result: {result.success}")
    if result.success:
        print(f"   Solution: {result.output_data}")

    # Cleanup
    await a2a_agent1.stop()
    await a2a_agent2.stop()
    print("\n✅ Agents stopped")


async def example_collaboration():
    """Example 3: Multi-agent collaboration"""
    print("\n" + "=" * 60)
    print("Example 3: Multi-Agent Collaboration")
    print("=" * 60)

    api_key = os.getenv("DATABRICKS_API_KEY")
    base_url = os.getenv("DATABRICKS_BASE_URL")

    if not api_key or not base_url:
        print("⚠️  Set DATABRICKS_API_KEY and DATABRICKS_BASE_URL to run this example")
        return

    # Create registry
    registry = AgentRegistry()

    # Create three agents for collaboration
    print("\n📦 Creating collaboration team...")
    agents = []
    for i, name in enumerate(["researcher", "analyst", "writer"]):
        client = UnifyLLM(provider="databricks", api_key=api_key, base_url=base_url)
        base_agent = Agent(
            config=AgentConfig(
                name=name,
                agent_type=AgentType.TOOLS,
                model="claude-opus-4-5",
                provider="databricks",
                system_prompt=f"You are a {name} expert.",
                max_iterations=3
            ),
            client=client
        )

        a2a_agent = A2AAgent(
            base_agent=base_agent,
            config=A2AAgentConfig(
                agent_name=name,
                capabilities=[
                    AgentCapability(
                        name=f"{name}_work",
                        description=f"Perform {name} work",
                        input_schema={"type": "object"},
                        output_schema={"type": "object"},
                        tags=[name]
                    )
                ]
            ),
            registry=registry
        )

        await a2a_agent.start()
        agents.append(a2a_agent)
        print(f"   ✅ {name} agent ready")

    # Test sequential collaboration
    print("\n🔄 Testing Sequential Collaboration...")
    collab_seq = AgentCollaboration(strategy=CollaborationStrategy.SEQUENTIAL)
    for agent in agents:
        collab_seq.add_agent(agent)

    result = await collab_seq.execute({
        "task": "research_and_write",
        "data": {"topic": "AI agents"}
    })
    print(f"✅ Sequential: {len(result.get('results', []))} steps completed")

    # Test parallel collaboration
    print("\n⚡ Testing Parallel Collaboration...")
    collab_par = AgentCollaboration(strategy=CollaborationStrategy.PARALLEL)
    for agent in agents:
        collab_par.add_agent(agent)

    result = await collab_par.execute({
        "task": "parallel_analysis",
        "data": {"topic": "Future trends"}
    })
    print(f"✅ Parallel: {len(result.get('results', []))} agents executed")

    # Test consensus collaboration
    print("\n🗳️  Testing Consensus Collaboration...")
    collab_cons = AgentCollaboration(strategy=CollaborationStrategy.CONSENSUS)
    for agent in agents:
        collab_cons.add_agent(agent)

    result = await collab_cons.execute({
        "task": "make_decision",
        "data": {"question": "Should we proceed?"},
        "voting_method": "majority"
    })
    print(f"✅ Consensus: {result.get('decision')}")

    # Cleanup
    for agent in agents:
        await agent.stop()
    print("\n✅ All agents stopped")


async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("🚀 MCP & A2A Quick Start Examples")
    print("   Powered by Databricks Claude Opus 4.5")
    print("=" * 60)

    # Example 1: MCP Server (doesn't require Databricks)
    await example_mcp_server()

    # Example 2: A2A Agents (requires Databricks)
    await example_a2a_agents()

    # Example 3: Collaboration (requires Databricks)
    await example_collaboration()

    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)
    print("\n📚 For more information:")
    print("   - Full Guide: docs/MCP_A2A_GUIDE.md")
    print("   - Run Tests: python tests/test_mcp_a2a_databricks.py")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
