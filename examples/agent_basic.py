"""Example: Basic agent with tools.

This example demonstrates how to create a simple AI agent with tool calling capabilities.
"""

import os
from unify_llm import UnifyLLM
from unify_llm.agent import (
    Agent,
    AgentConfig,
    AgentExecutor,
    ToolRegistry,
    ConversationMemory
)
from unify_llm.agent.builtin_tools import (
    create_calculator_tool,
    create_string_tools,
    create_data_formatter_tool
)


def main():
    # Initialize UnifyLLM client
    client = UnifyLLM(
        provider="openai",
        api_key=os.getenv("OPENAI_API_KEY")
    )

    # Create tool registry
    registry = ToolRegistry()

    # Register built-in tools
    registry.register(create_calculator_tool())
    for tool in create_string_tools():
        registry.register(tool)
    registry.register(create_data_formatter_tool())

    # Configure agent
    config = AgentConfig(
        name="assistant",
        model="gpt-4",
        provider="openai",
        system_prompt="""You are a helpful AI assistant with access to various tools.
You can perform calculations, manipulate strings, and format data.
Always use the appropriate tool when needed.""",
        temperature=0.7,
        max_iterations=10,
        enable_memory=True,
        memory_window=10,
        tools=["calculator", "to_uppercase", "to_lowercase", "reverse_string", "count_words", "format_data"]
    )

    # Create agent
    agent = Agent(config=config, client=client)

    # Create executor
    executor = AgentExecutor(
        agent=agent,
        tool_registry=registry,
        memory=ConversationMemory(window_size=10),
        verbose=True
    )

    print("=" * 60)
    print("AI Agent with Tools - Interactive Demo")
    print("=" * 60)
    print()

    # Example 1: Mathematical calculation
    print("Example 1: Mathematical Calculation")
    print("-" * 60)
    result = executor.run("What is the square root of 144 plus 25?")
    print(f"User: What is the square root of 144 plus 25?")
    print(f"Agent: {result.output}")
    print(f"Tool calls made: {len(result.tool_calls)}")
    print()

    # Example 2: String manipulation
    print("Example 2: String Manipulation")
    print("-" * 60)
    result = executor.run("Convert 'Hello World' to uppercase and then reverse it")
    print(f"User: Convert 'Hello World' to uppercase and then reverse it")
    print(f"Agent: {result.output}")
    print(f"Tool calls made: {len(result.tool_calls)}")
    print()

    # Example 3: Word counting
    print("Example 3: Word Counting")
    print("-" * 60)
    text = "The quick brown fox jumps over the lazy dog"
    result = executor.run(f"How many words are in this text: '{text}'?")
    print(f"User: How many words are in this text: '{text}'?")
    print(f"Agent: {result.output}")
    print(f"Tool calls made: {len(result.tool_calls)}")
    print()

    # Example 4: Complex task with multiple tools
    print("Example 4: Complex Task")
    print("-" * 60)
    result = executor.run(
        "Calculate the result of (15 * 3) + (sqrt(64) - 2), "
        "then tell me how many characters are in the result when written out."
    )
    print(f"User: Calculate (15 * 3) + (sqrt(64) - 2), then count characters in result")
    print(f"Agent: {result.output}")
    print(f"Tool calls made: {len(result.tool_calls)}")
    print()

    # Example 5: Conversational with memory
    print("Example 5: Conversational (with memory)")
    print("-" * 60)
    result = executor.run("Remember this number: 42")
    print(f"User: Remember this number: 42")
    print(f"Agent: {result.output}")
    print()

    result = executor.run("What number did I just ask you to remember? Multiply it by 2.")
    print(f"User: What number did I just ask you to remember? Multiply it by 2.")
    print(f"Agent: {result.output}")
    print()

    print("=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
