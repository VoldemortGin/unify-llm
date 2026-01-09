"""Integration test for UnifyLLM AI Agent functionality.

This script tests all major components of the Agent framework
to ensure everything is properly integrated and working.
"""

import sys

import rootutils

ROOT_DIR = rootutils.setup_root(search_from=__file__, indicator=[".project-root"], pythonpath=True)

def test_imports():
    """Test that all modules can be imported."""
    print("=" * 60)
    print("Test 1: Module Imports")
    print("=" * 60)

    try:
        # Core imports
        from src.agent import (
            Agent, AgentConfig, AgentType,
            Tool, ToolRegistry, ToolResult,
            ConversationMemory, SharedMemory,
            AgentExecutor,
            Workflow, WorkflowNode, WorkflowConfig, NodeType
        )
        print("✅ Core modules imported successfully")

        # Advanced imports
        from src.agent import (
            ParallelExecutor, ErrorHandler, AgentChain
        )
        print("✅ Advanced modules imported successfully")

        # Template imports
        from src.agent import AgentTemplates
        print("✅ Template module imported successfully")

        # Visualization imports
        from src.agent import (
            WorkflowVisualizer, ExecutionTracer, visualize_workflow
        )
        print("✅ Visualization modules imported successfully")

        # Monitoring imports
        from src.agent import (
            PerformanceMonitor, ExecutionLogger, AgentMetrics
        )
        print("✅ Monitoring modules imported successfully")

    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_tool_creation():
    """Test tool creation and registration."""
    print("\n" + "=" * 60)
    print("Test 2: Tool Creation")
    print("=" * 60)

    try:
        from src.agent import Tool, ToolRegistry, ToolParameter, ToolParameterType, ToolResult

        # Create a simple tool
        def add_numbers(a: int, b: int) -> ToolResult:
            return ToolResult(success=True, output=a + b)

        registry = ToolRegistry()
        registry.register_function(
            name="add",
            description="Add two numbers",
            function=add_numbers
        )

        tool = registry.get("add")
        assert tool is not None, "Tool not found in registry"

        # Test tool execution
        result = tool.execute(a=5, b=3)
        assert result.success, "Tool execution failed"
        assert result.output == 8, f"Expected 8, got {result.output}"

        print(f"✅ Tool created and executed successfully: 5 + 3 = {result.output}")
    except Exception as e:
        print(f"❌ Tool creation failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_builtin_tools():
    """Test built-in tools."""
    print("\n" + "=" * 60)
    print("Test 3: Built-in Tools")
    print("=" * 60)

    try:
        from src.agent import ToolRegistry
        from src.agent.builtin_tools import (
            create_calculator_tool,
            create_string_tools,
            create_data_formatter_tool
        )

        registry = ToolRegistry()

        # Register calculator
        calc = create_calculator_tool()
        registry.register(calc)
        result = calc.execute(expression="2 + 2")
        assert result.success, "Calculator failed"
        print(f"✅ Calculator: 2 + 2 = {result.output}")

        # Register string tools
        tools = create_string_tools()
        for tool in tools:
            registry.register(tool)

        uppercase_tool = registry.get("to_uppercase")
        result = uppercase_tool.execute(text="hello")
        assert result.output == "HELLO", "Uppercase tool failed"
        print(f"✅ String tools: 'hello' -> '{result.output}'")

        print(f"✅ Total tools registered: {len(registry.list_tools())}")
    except Exception as e:
        print(f"❌ Built-in tools test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_memory():
    """Test memory management."""
    print("\n" + "=" * 60)
    print("Test 4: Memory Management")
    print("=" * 60)

    try:
        from src.agent import ConversationMemory, SharedMemory

        # Test ConversationMemory
        memory = ConversationMemory(window_size=5)
        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi there!")
        memory.add_user_message("How are you?")

        messages = memory.get_messages()
        assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"
        print(f"✅ ConversationMemory: {len(messages)} messages stored")

        # Test SharedMemory
        shared = SharedMemory()
        shared.set("key1", "value1")
        shared.set("key2", {"nested": "data"})

        assert shared.get("key1") == "value1", "SharedMemory get failed"
        assert shared.has("key2"), "SharedMemory has failed"
        print(f"✅ SharedMemory: {len(shared.keys())} keys stored")

    except Exception as e:
        print(f"❌ Memory test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_agent_templates():
    """Test agent templates."""
    print("\n" + "=" * 60)
    print("Test 5: Agent Templates")
    print("=" * 60)

    try:
        from src.agent import AgentTemplates

        templates = [
            "research_assistant",
            "code_assistant",
            "data_analyst",
            "content_writer",
            "customer_support",
            "task_planner",
            "creative_brainstormer",
            "general_assistant"
        ]

        for template_name in templates:
            config = getattr(AgentTemplates, template_name)()
            assert config.name is not None, f"Template {template_name} has no name"
            print(f"  ✅ {template_name}: {config.name}")

        print(f"✅ All {len(templates)} templates loaded successfully")
    except Exception as e:
        print(f"❌ Template test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_workflow_creation():
    """Test workflow creation."""
    print("\n" + "=" * 60)
    print("Test 6: Workflow Creation")
    print("=" * 60)

    try:
        from src.agent import WorkflowConfig, WorkflowNode, NodeType

        nodes = [
            WorkflowNode(
                id="start",
                type=NodeType.AGENT,
                name="Start Node",
                agent_name="agent1",
                next_nodes=["end"]
            ),
            WorkflowNode(
                id="end",
                type=NodeType.AGENT,
                name="End Node",
                agent_name="agent2",
                next_nodes=[]
            )
        ]

        config = WorkflowConfig(
            name="test_workflow",
            description="Test workflow",
            start_node="start",
            nodes=nodes
        )

        assert config.name == "test_workflow", "Workflow name mismatch"
        assert len(config.nodes) == 2, f"Expected 2 nodes, got {len(config.nodes)}"
        print(f"✅ Workflow created: {config.name} with {len(config.nodes)} nodes")

    except Exception as e:
        print(f"❌ Workflow creation failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_visualization():
    """Test visualization utilities."""
    print("\n" + "=" * 60)
    print("Test 7: Visualization")
    print("=" * 60)

    try:
        from src.agent import (
            Workflow, WorkflowConfig, WorkflowNode, NodeType,
            WorkflowVisualizer
        )

        # Create simple workflow
        nodes = [
            WorkflowNode(
                id="step1",
                type=NodeType.AGENT,
                name="Step 1",
                agent_name="agent1",
                next_nodes=["step2"]
            ),
            WorkflowNode(
                id="step2",
                type=NodeType.AGENT,
                name="Step 2",
                agent_name="agent2",
                next_nodes=[]
            )
        ]

        config = WorkflowConfig(
            name="viz_test",
            description="Visualization test",
            start_node="step1",
            nodes=nodes
        )

        # Create mock workflow (without actual agents)
        class MockWorkflow:
            def __init__(self, config):
                self.config = config
                self.nodes = {node.id: node for node in config.nodes}

        workflow = MockWorkflow(config)
        viz = WorkflowVisualizer(workflow)

        # Test ASCII output
        ascii_output = viz.to_ascii()
        assert "viz_test" in ascii_output, "Workflow name not in ASCII output"
        print("✅ ASCII visualization generated")

        # Test Mermaid output
        mermaid_output = viz.to_mermaid()
        assert "graph TD" in mermaid_output, "Mermaid diagram invalid"
        print("✅ Mermaid diagram generated")

        # Test JSON output
        json_output = viz.to_json()
        assert "viz_test" in json_output, "Workflow name not in JSON"
        print("✅ JSON export generated")

    except Exception as e:
        print(f"❌ Visualization test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_monitoring():
    """Test monitoring utilities."""
    print("\n" + "=" * 60)
    print("Test 8: Monitoring")
    print("=" * 60)

    try:
        from src.agent import PerformanceMonitor, ExecutionLogger

        # Test PerformanceMonitor
        monitor = PerformanceMonitor()
        monitor.start_execution("test_agent")
        monitor.end_execution("test_agent", success=True, iterations=3, tool_calls=[])

        metrics = monitor.get_metrics("test_agent")
        assert metrics is not None, "No metrics found"
        assert metrics.total_executions == 1, "Execution count mismatch"
        print(f"✅ PerformanceMonitor: {metrics.total_executions} execution tracked")

        # Test ExecutionLogger
        logger = ExecutionLogger()

        class MockResult:
            success = True
            output = "test output"
            iterations = 2
            tool_calls = []
            error = None

        logger.log_execution(
            agent_name="test_agent",
            user_input="test input",
            result=MockResult()
        )

        history = logger.get_history("test_agent")
        assert len(history) == 1, "Log entry not found"
        print(f"✅ ExecutionLogger: {len(history)} entry logged")

    except Exception as e:
        print(f"❌ Monitoring test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("UnifyLLM AI Agent - Integration Test Suite")
    print("=" * 60)
    print()

    tests = [
        ("Module Imports", test_imports),
        ("Tool Creation", test_tool_creation),
        ("Built-in Tools", test_builtin_tools),
        ("Memory Management", test_memory),
        ("Agent Templates", test_agent_templates),
        ("Workflow Creation", test_workflow_creation),
        ("Visualization", test_visualization),
        ("Monitoring", test_monitoring),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            test_func()
            results.append((test_name, True))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print()
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 All tests passed! AI Agent framework is fully functional.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
