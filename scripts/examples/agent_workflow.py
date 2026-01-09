"""Example: Multi-agent workflow.

This example demonstrates how to create a multi-agent workflow
with sequential execution, similar to n8n's agent orchestration.
"""

import os
from src import UnifyLLM
from src.agent import (
    Agent,
    AgentConfig,
    AgentExecutor,
    Workflow,
    WorkflowConfig,
    WorkflowNode,
    NodeType,
    ToolRegistry,
    SharedMemory
)
from src.agent.builtin_tools import create_calculator_tool, create_string_tools


def main():
    # Initialize UnifyLLM client
    client = UnifyLLM(
        provider="openai",
        api_key=os.getenv("OPENAI_API_KEY")
    )

    # Create shared tool registry
    registry = ToolRegistry()
    registry.register(create_calculator_tool())
    for tool in create_string_tools():
        registry.register(tool)

    # Create specialized agents
    researcher_config = AgentConfig(
        name="researcher",
        model="gpt-4",
        provider="openai",
        system_prompt="""You are a research specialist. Your job is to gather and organize
information about a topic. Provide detailed, well-structured information.""",
        temperature=0.7,
        max_iterations=5,
        tools=["calculator"]
    )

    analyst_config = AgentConfig(
        name="analyst",
        model="gpt-4",
        provider="openai",
        system_prompt="""You are a data analyst. Your job is to analyze information
and extract key insights. Be analytical and thorough.""",
        temperature=0.5,
        max_iterations=5,
        tools=["calculator"]
    )

    writer_config = AgentConfig(
        name="writer",
        model="gpt-4",
        provider="openai",
        system_prompt="""You are a technical writer. Your job is to take complex
information and write clear, concise summaries. Be clear and engaging.""",
        temperature=0.8,
        max_iterations=5,
        tools=["count_words"]
    )

    # Create agent instances
    researcher = Agent(config=researcher_config, client=client)
    analyst = Agent(config=analyst_config, client=client)
    writer = Agent(config=writer_config, client=client)

    # Define workflow: Research -> Analyze -> Write
    workflow_config = WorkflowConfig(
        name="research_analyze_write",
        description="A workflow that researches a topic, analyzes it, and writes a summary",
        start_node="research",
        nodes=[
            WorkflowNode(
                id="research",
                type=NodeType.AGENT,
                name="Research Topic",
                agent_name="researcher",
                next_nodes=["analyze"],
                metadata={
                    "description": "Gather detailed information about the topic"
                }
            ),
            WorkflowNode(
                id="analyze",
                type=NodeType.AGENT,
                name="Analyze Information",
                agent_name="analyst",
                next_nodes=["write"],
                metadata={
                    "description": "Analyze the researched information for key insights"
                }
            ),
            WorkflowNode(
                id="write",
                type=NodeType.AGENT,
                name="Write Summary",
                agent_name="writer",
                next_nodes=[],
                metadata={
                    "description": "Write a clear summary based on the analysis"
                }
            )
        ],
        max_iterations=10,
        enable_shared_memory=True
    )

    # Create workflow
    workflow = Workflow(
        config=workflow_config,
        agents={
            "researcher": researcher,
            "analyst": analyst,
            "writer": writer
        },
        tool_registry=registry,
        shared_memory=SharedMemory(),
        verbose=True
    )

    print("=" * 60)
    print("Multi-Agent Workflow Demo")
    print("=" * 60)
    print()
    print("Workflow: Researcher -> Analyst -> Writer")
    print()

    # Example topic
    topic = "What are the key benefits of quantum computing?"

    print(f"Topic: {topic}")
    print()
    print("Executing workflow...")
    print("-" * 60)
    print()

    # Run workflow
    result = workflow.run(topic)

    # Display results
    if result.success:
        print("✓ Workflow completed successfully!")
        print()
        print("=" * 60)
        print("Node Results:")
        print("=" * 60)
        print()

        for node_id, node_result in result.node_results.items():
            node = workflow.nodes[node_id]
            print(f"Node: {node.name} ({node_id})")
            print("-" * 60)

            if hasattr(node_result, 'output'):
                print(f"Output: {node_result.output}")
                print(f"Iterations: {node_result.iterations}")
                print(f"Tool calls: {len(node_result.tool_calls)}")
            else:
                print(f"Result: {node_result}")

            print()

        print("=" * 60)
        print("Final Output:")
        print("=" * 60)
        print()
        print(result.output)
        print()

    else:
        print(f"✗ Workflow failed: {result.error}")

    print("=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
