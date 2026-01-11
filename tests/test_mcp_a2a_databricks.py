"""
Test MCP and A2A functionality with Databricks Claude Opus 4.5

This script demonstrates:
1. MCP client/server for exposing agent tools
2. A2A protocol for agent-to-agent communication
3. Multi-agent collaboration using Databricks Claude Opus 4.5

NOTE: This is an integration test that requires real API credentials.
Mark with @pytest.mark.integration to exclude from CI.
"""

import asyncio
import os

import pytest
import rootutils

ROOT_DIR = rootutils.setup_root(search_from=__file__, indicator=[".project-root"], pythonpath=True)

from unify_llm import UnifyLLM
from unify_llm.a2a import (
    A2AAgent,
    A2AAgentConfig,
    AgentRegistry,
    AgentDiscovery,
    AgentCollaboration,
    CollaborationStrategy,
    AgentCapability,
)
from unify_llm.agent import Agent, AgentConfig, AgentType
from unify_llm.mcp import MCPServer, MCPServerConfig


# Test 1: Basic Databricks connection
@pytest.mark.integration
@pytest.mark.asyncio
async def test_databricks_connection():
    """Test basic connection to Databricks Claude Opus 4.5"""
    print("\n" + "=" * 60)
    print("TEST 1: Testing Databricks Claude Opus 4.5 Connection")
    print("=" * 60)

    try:
        # Get credentials from environment
        api_key = os.getenv("DATABRICKS_API_KEY")
        base_url = os.getenv("DATABRICKS_BASE_URL")

        if not api_key or not base_url:
            print("❌ Error: DATABRICKS_API_KEY and DATABRICKS_BASE_URL must be set")
            return False

        # Initialize client with Claude Opus 4.5
        client = UnifyLLM(
            provider="databricks",
            api_key=api_key,
            base_url=base_url
        )

        # Test simple chat
        response = client.chat(
            model="claude-opus-4-5",  # or your Databricks endpoint name
            messages=[
                {"role": "user", "content": "Say 'Hello from Databricks Claude Opus 4.5!' in one sentence."}
            ],
            max_tokens=100
        )

        print(f"✅ Response: {response.content}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


# Test 2: MCP Server with Agent Tools
@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_server():
    """Test MCP server exposing agent tools"""
    print("\n" + "=" * 60)
    print("TEST 2: Testing MCP Server with Agent Tools")
    print("=" * 60)

    try:
        # Create MCP server
        config = MCPServerConfig(
            server_name="unify-llm-agent-server",
            server_version="1.0.0"
        )
        server = MCPServer(config)

        # Register calculator tool
        @server.tool("calculator", "Perform mathematical calculations", {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate"}
            },
            "required": ["expression"]
        })
        async def calculator(expression: str):
            try:
                result = eval(expression)
                return {"result": result, "expression": expression}
            except Exception as e:
                return {"error": str(e)}

        # Register a data resource
        @server.resource("file://agent_config.json", "application/json", "Agent configuration")
        async def get_config():
            return '{"name": "unify-agent", "version": "1.0.0", "capabilities": ["math", "text"]}'

        # Register a prompt template
        @server.prompt("math_problem", "Solve a math problem", [
            {"name": "problem", "description": "Math problem to solve", "required": True}
        ])
        async def math_prompt(problem: str):
            return {
                "messages": [
                    {"role": "system", "content": "You are a math expert."},
                    {"role": "user", "content": f"Solve this problem: {problem}"}
                ]
            }

        print("✅ MCP Server configured with:")
        print("   - Tool: calculator")
        print("   - Resource: agent_config.json")
        print("   - Prompt: math_problem")
        print("\n💡 Server ready to accept connections (would run with transport in production)")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


# Test 3: A2A Agent Communication
@pytest.mark.integration
@pytest.mark.asyncio
async def test_a2a_communication():
    """Test A2A protocol for agent communication"""
    print("\n" + "=" * 60)
    print("TEST 3: Testing A2A Agent Communication")
    print("=" * 60)

    try:
        # Get Databricks credentials
        api_key = os.getenv("DATABRICKS_API_KEY")
        base_url = os.getenv("DATABRICKS_BASE_URL")

        if not api_key or not base_url:
            print("❌ Error: Environment variables not set")
            return False

        # Create shared registry
        registry = AgentRegistry()

        # Create first agent - Math Expert
        client1 = UnifyLLM(provider="databricks", api_key=api_key, base_url=base_url)
        agent1_config = AgentConfig(
            name="math_expert",
            agent_type=AgentType.TOOLS,
            model="claude-opus-4-5",
            provider="databricks",
            system_prompt="You are a mathematics expert.",
            max_iterations=3
        )
        base_agent1 = Agent(config=agent1_config, client=client1)

        # Wrap with A2A capabilities
        a2a_config1 = A2AAgentConfig(
            agent_name="math_expert",
            capabilities=[
                AgentCapability(
                    name="solve_math",
                    description="Solve mathematical problems",
                    input_schema={"type": "object", "properties": {"problem": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"solution": {"type": "string"}}},
                    tags=["math", "calculation"]
                )
            ]
        )
        a2a_agent1 = A2AAgent(base_agent1, a2a_config1, registry)

        # Register handler for math capability
        @a2a_agent1.handle_capability("solve_math")
        async def handle_math(input_data):
            problem = input_data.get("problem", "")
            # Simulate solving
            return {"solution": f"Solution to '{problem}' is 42 (simulated)"}

        # Create second agent - Data Analyst
        client2 = UnifyLLM(provider="databricks", api_key=api_key, base_url=base_url)
        agent2_config = AgentConfig(
            name="data_analyst",
            agent_type=AgentType.TOOLS,
            model="claude-opus-4-5",
            provider="databricks",
            system_prompt="You are a data analysis expert.",
            max_iterations=3
        )
        base_agent2 = Agent(config=agent2_config, client=client2)

        a2a_config2 = A2AAgentConfig(
            agent_name="data_analyst",
            capabilities=[
                AgentCapability(
                    name="analyze_data",
                    description="Analyze datasets",
                    input_schema={"type": "object", "properties": {"dataset": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"analysis": {"type": "string"}}},
                    tags=["data", "analysis"]
                )
            ]
        )
        a2a_agent2 = A2AAgent(base_agent2, a2a_config2, registry)

        # Start both agents
        await a2a_agent1.start()
        await a2a_agent2.start()

        print("✅ Created two A2A agents:")
        print(f"   - Agent 1: {a2a_agent1.agent_id} (math_expert)")
        print(f"   - Agent 2: {a2a_agent2.agent_id} (data_analyst)")

        # Test discovery
        discovery = AgentDiscovery(registry)
        math_agents = await discovery.discover(capabilities=["solve_math"])
        print(f"\n✅ Discovered {len(math_agents)} agent(s) with 'solve_math' capability")

        # Test task delegation
        print("\n🔄 Testing task delegation...")
        result = await a2a_agent2.delegate_task(
            target_agent_id=a2a_agent1.agent_id,
            capability="solve_math",
            input_data={"problem": "What is 15 * 23?"}
        )
        print(f"✅ Delegation result: {result.model_dump()}")

        # Cleanup
        await a2a_agent1.stop()
        await a2a_agent2.stop()

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


# Test 4: Multi-Agent Collaboration
@pytest.mark.integration
@pytest.mark.asyncio
async def test_collaboration():
    """Test multi-agent collaboration with different strategies"""
    print("\n" + "=" * 60)
    print("TEST 4: Testing Multi-Agent Collaboration")
    print("=" * 60)

    try:
        # Get Databricks credentials
        api_key = os.getenv("DATABRICKS_API_KEY")
        base_url = os.getenv("DATABRICKS_BASE_URL")

        if not api_key or not base_url:
            print("❌ Error: Environment variables not set")
            return False

        # Create registry
        registry = AgentRegistry()

        # Create three agents for collaboration
        agents = []
        for i, name in enumerate(["researcher", "analyst", "writer"]):
            client = UnifyLLM(provider="databricks", api_key=api_key, base_url=base_url)
            agent_config = AgentConfig(
                name=name,
                agent_type=AgentType.TOOLS,
                model="claude-opus-4-5",
                provider="databricks",
                system_prompt=f"You are a {name} expert.",
                max_iterations=3
            )
            base_agent = Agent(config=agent_config, client=client)

            a2a_config = A2AAgentConfig(
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
            )
            a2a_agent = A2AAgent(base_agent, a2a_config, registry)
            await a2a_agent.start()
            agents.append(a2a_agent)

        print(f"✅ Created {len(agents)} agents for collaboration")

        # Test sequential collaboration
        collab = AgentCollaboration(strategy=CollaborationStrategy.SEQUENTIAL)
        for agent in agents:
            collab.add_agent(agent)

        print("\n🔄 Testing sequential collaboration...")
        result = await collab.execute({
            "task": "research_and_write",
            "data": {"topic": "AI agents"}
        })
        print(f"✅ Sequential result: {len(result.get('results', []))} steps completed")

        # Test parallel collaboration
        collab_parallel = AgentCollaboration(strategy=CollaborationStrategy.PARALLEL)
        for agent in agents:
            collab_parallel.add_agent(agent)

        print("\n🔄 Testing parallel collaboration...")
        result = await collab_parallel.execute({
            "task": "parallel_analysis",
            "data": {"topic": "AI trends"}
        })
        print(f"✅ Parallel result: {len(result.get('results', []))} agents executed")

        # Test consensus collaboration
        collab_consensus = AgentCollaboration(strategy=CollaborationStrategy.CONSENSUS)
        for agent in agents:
            collab_consensus.add_agent(agent)

        print("\n🔄 Testing consensus collaboration...")
        result = await collab_consensus.execute({
            "task": "make_decision",
            "data": {"question": "Should we proceed?"},
            "voting_method": "majority"
        })
        print(f"✅ Consensus result: {result.get('decision')}")

        # Cleanup
        for agent in agents:
            await agent.stop()

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


# Main test runner
async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🚀 UnifyLLM MCP & A2A Testing Suite")
    print("    with Databricks Claude Opus 4.5")
    print("=" * 60)

    # Check environment variables
    print("\n📋 Checking environment variables...")
    api_key = os.getenv("DATABRICKS_API_KEY")
    base_url = os.getenv("DATABRICKS_BASE_URL")

    if not api_key:
        print("⚠️  DATABRICKS_API_KEY not set")
    else:
        print(f"✅ DATABRICKS_API_KEY: {api_key[:10]}...")

    if not base_url:
        print("⚠️  DATABRICKS_BASE_URL not set")
    else:
        print(f"✅ DATABRICKS_BASE_URL: {base_url}")

    if not api_key or not base_url:
        print("\n❌ Please set DATABRICKS_API_KEY and DATABRICKS_BASE_URL environment variables")
        print("\nExample:")
        print('export DATABRICKS_API_KEY="dapi..."')
        print('export DATABRICKS_BASE_URL="https://your-workspace.cloud.databricks.com"')
        return

    # Run tests
    results = {}

    results["connection"] = await test_databricks_connection()
    results["mcp_server"] = await test_mcp_server()
    results["a2a_comm"] = await test_a2a_communication()
    results["collaboration"] = await test_collaboration()

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")


if __name__ == "__main__":
    asyncio.run(main())
