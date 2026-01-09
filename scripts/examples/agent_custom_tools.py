"""Example: Custom tools for AI agents.

This example shows how to create custom tools for specific tasks.
"""

import os
import requests
from typing import List, Dict, Any
from src import UnifyLLM
from src.agent import (
    Agent,
    AgentConfig,
    AgentExecutor,
    Tool,
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolRegistry,
)


def create_weather_tool() -> Tool:
    """Create a mock weather tool."""

    def get_weather(city: str) -> ToolResult:
        """Get weather for a city (mock implementation).

        Args:
            city: City name

        Returns:
            Weather information
        """
        # This is a mock implementation
        # In production, you would call a real weather API
        mock_weather = {
            "New York": {"temp": 72, "condition": "Sunny", "humidity": 65},
            "London": {"temp": 61, "condition": "Cloudy", "humidity": 78},
            "Tokyo": {"temp": 68, "condition": "Rainy", "humidity": 82},
            "Paris": {"temp": 64, "condition": "Partly Cloudy", "humidity": 70},
        }

        weather = mock_weather.get(city, {"temp": 70, "condition": "Unknown", "humidity": 50})

        return ToolResult(
            success=True,
            output={
                "city": city,
                "temperature": weather["temp"],
                "condition": weather["condition"],
                "humidity": weather["humidity"],
                "unit": "Fahrenheit"
            },
            metadata={"source": "mock_api"}
        )

    return Tool(
        name="get_weather",
        description="Get current weather information for a city",
        parameters={
            "city": ToolParameter(
                type=ToolParameterType.STRING,
                description="Name of the city to get weather for",
                required=True
            )
        },
        function=get_weather
    )


def create_todo_tools() -> List[Tool]:
    """Create TODO list management tools."""

    # Shared TODO list storage
    todo_list: List[Dict[str, Any]] = []

    def add_todo(task: str, priority: str = "medium") -> ToolResult:
        """Add a task to the TODO list."""
        todo_item = {
            "id": len(todo_list) + 1,
            "task": task,
            "priority": priority,
            "completed": False
        }
        todo_list.append(todo_item)

        return ToolResult(
            success=True,
            output=f"Added task #{todo_item['id']}: {task}",
            metadata={"task_id": todo_item["id"]}
        )

    def list_todos() -> ToolResult:
        """List all TODO items."""
        if not todo_list:
            return ToolResult(
                success=True,
                output="No tasks in the TODO list",
                metadata={"count": 0}
            )

        return ToolResult(
            success=True,
            output=todo_list.copy(),
            metadata={"count": len(todo_list)}
        )

    def complete_todo(task_id: int) -> ToolResult:
        """Mark a TODO item as completed."""
        for item in todo_list:
            if item["id"] == task_id:
                item["completed"] = True
                return ToolResult(
                    success=True,
                    output=f"Completed task #{task_id}: {item['task']}",
                    metadata={"task_id": task_id}
                )

        return ToolResult(
            success=False,
            error=f"Task #{task_id} not found"
        )

    tools = []

    # Add TODO tool
    tools.append(Tool(
        name="add_todo",
        description="Add a new task to the TODO list",
        parameters={
            "task": ToolParameter(
                type=ToolParameterType.STRING,
                description="Task description",
                required=True
            ),
            "priority": ToolParameter(
                type=ToolParameterType.STRING,
                description="Task priority: low, medium, or high",
                required=False,
                enum=["low", "medium", "high"],
                default="medium"
            )
        },
        function=add_todo
    ))

    # List TODOs tool
    tools.append(Tool(
        name="list_todos",
        description="List all tasks in the TODO list",
        parameters={},
        function=list_todos
    ))

    # Complete TODO tool
    tools.append(Tool(
        name="complete_todo",
        description="Mark a task as completed",
        parameters={
            "task_id": ToolParameter(
                type=ToolParameterType.INTEGER,
                description="ID of the task to complete",
                required=True
            )
        },
        function=complete_todo
    ))

    return tools


def main():
    # Initialize UnifyLLM client
    client = UnifyLLM(
        provider="openai",
        api_key=os.getenv("OPENAI_API_KEY")
    )

    # Create tool registry and register custom tools
    registry = ToolRegistry()
    registry.register(create_weather_tool())
    for tool in create_todo_tools():
        registry.register(tool)

    # Configure agent with custom tools
    config = AgentConfig(
        name="personal_assistant",
        model="gpt-4",
        provider="openai",
        system_prompt="""You are a helpful personal assistant with access to weather
information and TODO list management. Help users manage their tasks and get weather updates.""",
        temperature=0.7,
        max_iterations=10,
        enable_memory=True,
        tools=["get_weather", "add_todo", "list_todos", "complete_todo"]
    )

    # Create agent and executor
    agent = Agent(config=config, client=client)
    executor = AgentExecutor(
        agent=agent,
        tool_registry=registry,
        verbose=True
    )

    print("=" * 60)
    print("Custom Tools Demo - Personal Assistant")
    print("=" * 60)
    print()

    # Example 1: Get weather
    print("Example 1: Weather Query")
    print("-" * 60)
    result = executor.run("What's the weather like in New York?")
    print(f"User: What's the weather like in New York?")
    print(f"Agent: {result.output}")
    print()

    # Example 2: Add tasks
    print("Example 2: Add TODO Tasks")
    print("-" * 60)
    result = executor.run(
        "Add these tasks to my TODO list: "
        "1. Buy groceries (high priority), "
        "2. Call dentist (medium priority), "
        "3. Read a book (low priority)"
    )
    print(f"User: Add three tasks with different priorities")
    print(f"Agent: {result.output}")
    print()

    # Example 3: List tasks
    print("Example 3: List All Tasks")
    print("-" * 60)
    result = executor.run("Show me my TODO list")
    print(f"User: Show me my TODO list")
    print(f"Agent: {result.output}")
    print()

    # Example 4: Complete a task
    print("Example 4: Complete a Task")
    print("-" * 60)
    result = executor.run("Mark task #1 as completed")
    print(f"User: Mark task #1 as completed")
    print(f"Agent: {result.output}")
    print()

    # Example 5: Complex query
    print("Example 5: Complex Multi-Tool Query")
    print("-" * 60)
    result = executor.run(
        "What's the weather in London? "
        "If it's rainy, add 'Bring umbrella' to my TODO list with high priority."
    )
    print(f"User: Weather-based TODO addition")
    print(f"Agent: {result.output}")
    print()

    print("=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
