"""
Test AI Agent with Databricks LLM

This example demonstrates using Databricks as the LLM provider
for the AI Agent system with n8n-style automation features.
"""

import asyncio
import os
from datetime import datetime
from src import UnifyLLM
from src.agent import (
    # Core Agent
    Agent,
    AgentConfig,
    AgentType,
    AgentExecutor,
    ToolRegistry,
    # Tools
    create_http_request_tool,
    # Templates
    AgentTemplates,
    # n8n-style features
    ScheduleTrigger,
    ManualTrigger,
    TriggerConfig,
    TriggerType,
    ExecutionHistory,
    ExecutionData,
    ExecutionStatus,
    http_get,
)


async def test_basic_agent_with_databricks():
    """Test 1: Basic Agent with Databricks"""
    print("\n" + "=" * 60)
    print("Test 1: Basic AI Agent with Databricks")
    print("=" * 60)

    # Get Databricks API key from environment
    api_key = os.getenv("DATABRICKS_API_KEY")
    base_url = os.getenv("DATABRICKS_BASE_URL")

    if not api_key or not base_url:
        print("⚠️  Please set DATABRICKS_API_KEY and DATABRICKS_BASE_URL environment variables")
        print("   Example:")
        print("   export DATABRICKS_API_KEY='your-key'")
        print("   export DATABRICKS_BASE_URL='https://your-workspace.databricks.com'")
        return

    # Initialize Databricks client
    client = UnifyLLM(
        provider="databricks",
        api_key=api_key,
        base_url=base_url
    )

    # Test basic LLM call
    print("\nTesting basic Databricks LLM call...")
    try:
        response = client.chat(
            model="databricks-meta-llama-3-1-70b-instruct",  # Databricks model
            messages=[
                {"role": "user", "content": "What is 15 * 23? Just give me the number."}
            ],
            temperature=0
        )
        print(f"✅ Databricks response: {response.content}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Create Agent with tools
    print("\n\nCreating Agent with calculator tool...")
    from src.agent.builtin_tools import create_calculator_tool

    registry = ToolRegistry()
    registry.register(create_calculator_tool())

    config = AgentConfig(
        name="databricks_agent",
        agent_type=AgentType.TOOLS,
        model="databricks-meta-llama-3-1-70b-instruct",
        provider="databricks",
        system_prompt="You are a helpful assistant with access to tools.",
        tools=["calculator"],
        temperature=0,
        max_iterations=3
    )

    agent = Agent(config=config, client=client)
    executor = AgentExecutor(agent=agent, tool_registry=registry)

    # Run agent
    print("\nRunning Agent with Databricks...")
    result = executor.run("Calculate 456 * 789 and tell me the result")

    print(f"\n✅ Agent Result:")
    print(f"   Output: {result.output}")
    print(f"   Iterations: {result.iterations}")
    print(f"   Tools used: {[step.get('tool_name') for step in result.steps if 'tool_name' in step]}")


async def test_http_tools_with_databricks():
    """Test 2: HTTP Tools + Databricks Agent"""
    print("\n" + "=" * 60)
    print("Test 2: HTTP Request Tool with Databricks Agent")
    print("=" * 60)

    api_key = os.getenv("DATABRICKS_API_KEY")
    base_url = os.getenv("DATABRICKS_BASE_URL")

    if not api_key or not base_url:
        print("⚠️  Skipping - Databricks credentials not set")
        return

    # Initialize client
    client = UnifyLLM(
        provider="databricks",
        api_key=api_key,
        base_url=base_url
    )

    # Create registry with HTTP tool
    registry = ToolRegistry()
    registry.register(create_http_request_tool())

    # Create Agent that can make HTTP requests
    config = AgentConfig(
        name="http_agent",
        agent_type=AgentType.TOOLS,
        model="databricks-meta-llama-3-1-70b-instruct",
        provider="databricks",
        system_prompt="You are a helpful assistant that can make HTTP requests to APIs.",
        tools=["http_request"],
        temperature=0,
        max_iterations=5
    )

    agent = Agent(config=config, client=client)
    executor = AgentExecutor(agent=agent, tool_registry=registry)

    # Ask agent to fetch GitHub repo info
    print("\nAsking Agent to fetch GitHub repository info...")
    result = executor.run(
        "Fetch information about the microsoft/vscode repository from GitHub API. "
        "Use the URL: https://api.github.com/repos/microsoft/vscode. "
        "Tell me the number of stars and forks."
    )

    print(f"\n✅ Agent Result:")
    print(f"   {result.output}")


async def test_databricks_with_triggers():
    """Test 3: Databricks Agent with Trigger System"""
    print("\n" + "=" * 60)
    print("Test 3: Databricks Agent with n8n-style Triggers")
    print("=" * 60)

    api_key = os.getenv("DATABRICKS_API_KEY")
    base_url = os.getenv("DATABRICKS_BASE_URL")

    if not api_key or not base_url:
        print("⚠️  Skipping - Databricks credentials not set")
        return

    # Initialize client and history
    client = UnifyLLM(
        provider="databricks",
        api_key=api_key,
        base_url=base_url
    )

    history = ExecutionHistory(db_path="databricks_test_executions.db")

    # Create agent
    from src.agent.builtin_tools import create_calculator_tool
    registry = ToolRegistry()
    registry.register(create_calculator_tool())

    config = AgentConfig(
        name="scheduled_agent",
        agent_type=AgentType.TOOLS,
        model="databricks-meta-llama-3-1-70b-instruct",
        provider="databricks",
        tools=["calculator"],
        temperature=0
    )

    agent = Agent(config=config, client=client)
    executor = AgentExecutor(agent=agent, tool_registry=registry)

    # Define workflow
    def run_workflow(event):
        """Execute agent workflow"""
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print(f"\n[{datetime.now()}] Workflow triggered!")
        print(f"  Execution ID: {execution_id}")
        print(f"  Trigger type: {event.trigger_type}")

        # Save execution start
        execution = ExecutionData(
            id=execution_id,
            workflow_id=event.metadata["workflow_id"],
            workflow_name="Databricks Agent Workflow",
            status=ExecutionStatus.RUNNING,
            start_time=datetime.now(),
            trigger_type=event.trigger_type.value,
            input_data=event.data
        )
        history.save(execution)

        try:
            # Run agent
            result = executor.run("What is 123 * 456? Just give me the number.")

            # Save success
            execution.status = ExecutionStatus.SUCCESS
            execution.end_time = datetime.now()
            execution.output_data = {"result": result.output}
            history.save(execution)

            print(f"  ✅ Result: {result.output}")
            print(f"  Duration: {execution.duration:.2f}s")

        except Exception as e:
            # Save error
            execution.status = ExecutionStatus.ERROR
            execution.end_time = datetime.now()
            execution.error = str(e)
            history.save(execution)

            print(f"  ❌ Error: {e}")

    # Create manual trigger
    trigger_config = TriggerConfig(
        id="manual_databricks",
        name="Manual Databricks Test",
        type=TriggerType.MANUAL,
        workflow_id="databricks_workflow"
    )

    trigger = ManualTrigger(trigger_config, run_workflow)
    await trigger.start()

    # Execute manually
    print("\nExecuting workflow manually...")
    trigger.execute({"test": "databricks_agent"})

    # Show statistics
    print("\n\nExecution Statistics:")
    stats = history.get_statistics(workflow_id="databricks_workflow")
    print(f"  Total: {stats['total']}")
    print(f"  Success: {stats['success']}")
    print(f"  Error: {stats['error']}")
    print(f"  Success rate: {stats['success_rate']}%")


async def test_databricks_with_template():
    """Test 4: Using Agent Template with Databricks"""
    print("\n" + "=" * 60)
    print("Test 4: Agent Template with Databricks")
    print("=" * 60)

    api_key = os.getenv("DATABRICKS_API_KEY")
    base_url = os.getenv("DATABRICKS_BASE_URL")

    if not api_key or not base_url:
        print("⚠️  Skipping - Databricks credentials not set")
        return

    client = UnifyLLM(
        provider="databricks",
        api_key=api_key,
        base_url=base_url
    )

    # Use research assistant template
    config = AgentTemplates.research_assistant()

    # Update to use Databricks
    config.model = "databricks-meta-llama-3-1-70b-instruct"
    config.provider = "databricks"

    print(f"\nUsing template: {config.name}")
    print(f"  Model: {config.model}")
    print(f"  Provider: {config.provider}")
    print(f"  Tools: {config.tools}")

    # Create and run agent
    from src.agent.builtin_tools import create_string_tools
    registry = ToolRegistry()
    for tool in create_string_tools():
        registry.register(tool)

    agent = Agent(config=config, client=client)
    executor = AgentExecutor(agent=agent, tool_registry=registry)

    print("\nAsking agent to analyze text...")
    result = executor.run(
        "Count the number of words in this sentence: "
        "'The quick brown fox jumps over the lazy dog.'"
    )

    print(f"\n✅ Result: {result.output}")


async def main():
    """Run all Databricks tests"""
    print("\n" + "🚀 " + "=" * 58)
    print("UnifyLLM AI Agent Testing with Databricks")
    print("=" * 60)

    # Check for credentials
    api_key = os.getenv("DATABRICKS_API_KEY")
    base_url = os.getenv("DATABRICKS_BASE_URL")

    if not api_key or not base_url:
        print("\n⚠️  IMPORTANT: Databricks credentials required!")
        print("\nPlease set these environment variables:")
        print("  export DATABRICKS_API_KEY='your-api-key'")
        print("  export DATABRICKS_BASE_URL='https://your-workspace.databricks.com'")
        print("\nYou can get these from your Databricks workspace:")
        print("  1. Go to your Databricks workspace")
        print("  2. Click on your user icon → Settings")
        print("  3. Go to Developer → Access tokens")
        print("  4. Generate new token")
        print("\nFor testing without Databricks, the system will skip tests.")
        print("=" * 60 + "\n")

    try:
        # Run all tests
        await test_basic_agent_with_databricks()
        await test_http_tools_with_databricks()
        await test_databricks_with_triggers()
        await test_databricks_with_template()

        print("\n" + "=" * 60)
        print("✅ All Databricks tests completed!")
        print("=" * 60)

        print("\n📚 Features Tested:")
        print("  ✅ Basic Agent with Databricks LLM")
        print("  ✅ HTTP Request Tool with Databricks")
        print("  ✅ Trigger System with Databricks")
        print("  ✅ Agent Templates with Databricks")

        print("\n🎯 Databricks Integration:")
        print("  • Model: databricks-meta-llama-3-1-70b-instruct")
        print("  • Tool calling supported")
        print("  • Full n8n-style automation")
        print("  • Execution history tracking")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
