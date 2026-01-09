"""Example: Advanced agent features including parallel execution and error handling.

This example demonstrates advanced capabilities:
- Parallel agent execution
- Error handling and retries
- Agent chaining
- Using agent templates
"""

import os
from src import UnifyLLM
from src.agent import (
    Agent,
    AgentExecutor,
    ToolRegistry,
)
from src.agent.templates import AgentTemplates
from src.agent.advanced import ParallelExecutor, ErrorHandler, AgentChain
from src.agent.builtin_tools import create_calculator_tool, create_string_tools
from src.agent.extended_tools import create_datetime_tools, create_text_analysis_tools


def demo_parallel_execution():
    """Demonstrate parallel agent execution."""
    print("=" * 60)
    print("Demo: Parallel Agent Execution")
    print("=" * 60)
    print()

    # Initialize client
    client = UnifyLLM(provider="openai", api_key=os.getenv("OPENAI_API_KEY"))

    # Create tool registry
    registry = ToolRegistry()
    for tool in create_string_tools():
        registry.register(tool)

    # Create three specialized agents
    agent1_config = AgentTemplates.data_analyst()
    agent2_config = AgentTemplates.content_writer()
    agent3_config = AgentTemplates.task_planner()

    agent1 = Agent(config=agent1_config, client=client)
    agent2 = Agent(config=agent2_config, client=client)
    agent3 = Agent(config=agent3_config, client=client)

    executor1 = AgentExecutor(agent=agent1, tool_registry=registry)
    executor2 = AgentExecutor(agent=agent2, tool_registry=registry)
    executor3 = AgentExecutor(agent=agent3, tool_registry=registry)

    # Execute in parallel
    print("Executing 3 agents in parallel...")
    print()

    parallel = ParallelExecutor(max_workers=3)
    results = parallel.execute_parallel(
        agents=[agent1, agent2, agent3],
        executors=[executor1, executor2, executor3],
        inputs=[
            "Analyze the trend: Sales increased 25% in Q1",
            "Write a brief summary about renewable energy",
            "Plan tasks for launching a mobile app"
        ]
    )

    # Display results
    for i, result in enumerate(results, 1):
        print(f"Agent {i} Result:")
        print("-" * 60)
        if result.success:
            print(f"✓ Success")
            print(f"Output: {result.output[:200]}...")
        else:
            print(f"✗ Failed: {result.error}")
        print()


def demo_error_handling():
    """Demonstrate error handling and retry logic."""
    print("=" * 60)
    print("Demo: Error Handling with Retry")
    print("=" * 60)
    print()

    client = UnifyLLM(provider="openai", api_key=os.getenv("OPENAI_API_KEY"))

    # Create agent
    config = AgentTemplates.general_assistant()
    agent = Agent(config=config, client=client)

    registry = ToolRegistry()
    registry.register(create_calculator_tool())

    executor = AgentExecutor(agent=agent, tool_registry=registry)

    # Create error handler
    handler = ErrorHandler(
        max_retries=3,
        backoff_factor=1.5,
        retry_on_errors=["timeout", "rate_limit", "api_error"]
    )

    # Execute with retry
    print("Executing with automatic retry on errors...")
    print()

    error_count = [0]

    def on_error(msg):
        error_count[0] += 1
        print(f"⚠️  {msg}")

    result = handler.execute_with_retry(
        executor=executor,
        user_input="Calculate: 123 * 456 + 789",
        on_error=on_error
    )

    if result.success:
        print(f"✓ Success after {error_count[0]} retries")
        print(f"Result: {result.output}")
    else:
        print(f"✗ Failed after {error_count[0]} attempts")
        print(f"Error: {result.error}")
    print()


def demo_agent_chain():
    """Demonstrate agent chaining."""
    print("=" * 60)
    print("Demo: Agent Chain (Research → Analyze → Write)")
    print("=" * 60)
    print()

    client = UnifyLLM(provider="openai", api_key=os.getenv("OPENAI_API_KEY"))

    # Create registry
    registry = ToolRegistry()
    registry.register(create_calculator_tool())

    # Create specialized agents for the chain
    researcher = Agent(config=AgentTemplates.research_assistant(), client=client)
    analyst = Agent(config=AgentTemplates.data_analyst(), client=client)
    writer = Agent(config=AgentTemplates.content_writer(), client=client)

    researcher_exec = AgentExecutor(agent=researcher, tool_registry=registry)
    analyst_exec = AgentExecutor(agent=analyst, tool_registry=registry)
    writer_exec = AgentExecutor(agent=writer, tool_registry=registry)

    # Build chain
    chain = AgentChain()

    chain.add_agent(
        researcher,
        researcher_exec,
        name="research",
        transform=None
    ).add_agent(
        analyst,
        analyst_exec,
        name="analyze",
        transform=lambda prev: f"Analyze this information and extract key insights: {prev}"
    ).add_agent(
        writer,
        writer_exec,
        name="write",
        transform=lambda prev: f"Write a concise summary based on this analysis: {prev}"
    )

    # Execute chain
    print("Executing chain: Research → Analyze → Write")
    print()

    result = chain.execute("What are the benefits of cloud computing?")

    # Display results
    print("Chain Results:")
    print("=" * 60)

    for step_name, step_data in result["steps"].items():
        print(f"\nStep: {step_name}")
        print("-" * 60)
        print(f"Success: {step_data['success']}")
        if step_data['success']:
            output = step_data['result'].output
            print(f"Output: {output[:150]}...")

    print()
    print("Final Output:")
    print("=" * 60)
    print(result["final_output"])
    print()


def demo_agent_templates():
    """Demonstrate using pre-configured agent templates."""
    print("=" * 60)
    print("Demo: Agent Templates")
    print("=" * 60)
    print()

    client = UnifyLLM(provider="openai", api_key=os.getenv("OPENAI_API_KEY"))

    # Create registry with extended tools
    registry = ToolRegistry()
    registry.register(create_calculator_tool())
    for tool in create_datetime_tools():
        registry.register(tool)
    for tool in create_text_analysis_tools():
        registry.register(tool)

    # Use different templates
    templates = [
        ("Research Assistant", AgentTemplates.research_assistant(tools=["calculator"])),
        ("Code Assistant", AgentTemplates.code_assistant()),
        ("Data Analyst", AgentTemplates.data_analyst(tools=["calculator"])),
        ("Content Writer", AgentTemplates.content_writer(tools=["count_words", "analyze_text_stats"])),
    ]

    for template_name, config in templates:
        print(f"Template: {template_name}")
        print(f"  Name: {config.name}")
        print(f"  Type: {config.agent_type}")
        print(f"  Temperature: {config.temperature}")
        print(f"  Max Iterations: {config.max_iterations}")
        print(f"  Tools: {', '.join(config.tools) if config.tools else 'None'}")
        print()


def main():
    """Run all demos."""
    print("\n")
    print("*" * 60)
    print("Advanced AI Agent Features Demo")
    print("*" * 60)
    print("\n")

    # Run demos
    try:
        demo_agent_templates()
        print("\n")

        # Uncomment to run these demos (require API key)
        # demo_parallel_execution()
        # print("\n")
        #
        # demo_error_handling()
        # print("\n")
        #
        # demo_agent_chain()

    except Exception as e:
        print(f"Error running demo: {e}")
        import traceback
        traceback.print_exc()

    print("*" * 60)
    print("Demo completed!")
    print("*" * 60)


if __name__ == "__main__":
    main()
