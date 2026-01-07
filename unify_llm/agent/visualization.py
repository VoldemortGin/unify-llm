"""Workflow visualization and debugging utilities."""

from typing import Dict, List, Any, Optional
from unify_llm.agent.workflow import Workflow, WorkflowNode, NodeType
import json


class WorkflowVisualizer:
    """Visualize workflows in different formats.

    Example:
        ```python
        from unify_llm.agent.visualization import WorkflowVisualizer

        viz = WorkflowVisualizer(workflow)

        # Print ASCII diagram
        print(viz.to_ascii())

        # Get Mermaid diagram
        print(viz.to_mermaid())

        # Export as JSON
        print(viz.to_json())
        ```
    """

    def __init__(self, workflow: Workflow):
        """Initialize visualizer.

        Args:
            workflow: Workflow to visualize
        """
        self.workflow = workflow
        self.config = workflow.config

    def to_ascii(self) -> str:
        """Generate ASCII diagram of workflow.

        Returns:
            ASCII diagram string
        """
        lines = []
        lines.append(f"Workflow: {self.config.name}")
        lines.append("=" * 60)
        lines.append(f"Description: {self.config.description}")
        lines.append(f"Start Node: {self.config.start_node}")
        lines.append("")
        lines.append("Flow:")
        lines.append("-" * 60)

        # Build flow representation
        visited = set()
        self._build_ascii_flow(self.config.start_node, lines, visited, indent=0)

        return "\n".join(lines)

    def _build_ascii_flow(
        self,
        node_id: str,
        lines: List[str],
        visited: set,
        indent: int = 0
    ):
        """Recursively build ASCII flow.

        Args:
            node_id: Current node ID
            lines: Lines to append to
            visited: Set of visited nodes
            indent: Current indentation level
        """
        if not node_id or node_id in visited:
            return

        visited.add(node_id)
        node = self.workflow.nodes.get(node_id)

        if not node:
            return

        # Add node representation
        prefix = "  " * indent
        node_type_symbol = {
            NodeType.AGENT: "🤖",
            NodeType.CONDITION: "🔀",
            NodeType.HUMAN_IN_LOOP: "👤",
            NodeType.PARALLEL: "⚡",
            NodeType.SEQUENTIAL: "➡️"
        }.get(node.type, "◯")

        lines.append(f"{prefix}{node_type_symbol} [{node.id}] {node.name}")
        lines.append(f"{prefix}   Type: {node.type}")

        if node.agent_name:
            lines.append(f"{prefix}   Agent: {node.agent_name}")

        # Add next nodes
        if node.next_nodes:
            for next_node_id in node.next_nodes:
                lines.append(f"{prefix}   ↓")
                self._build_ascii_flow(next_node_id, lines, visited, indent)

    def to_mermaid(self) -> str:
        """Generate Mermaid diagram syntax.

        Returns:
            Mermaid diagram string
        """
        lines = ["graph TD"]

        # Add nodes
        for node_id, node in self.workflow.nodes.items():
            # Determine node shape based on type
            if node.type == NodeType.AGENT:
                shape = f"[{node.name}]"
            elif node.type == NodeType.CONDITION:
                shape = f"{{{node.name}}}"
            elif node.type == NodeType.HUMAN_IN_LOOP:
                shape = f"[/{node.name}/]"
            else:
                shape = f"({node.name})"

            lines.append(f"    {node_id}{shape}")

        # Add connections
        for node_id, node in self.workflow.nodes.items():
            for next_id in node.next_nodes:
                lines.append(f"    {node_id} --> {next_id}")

        return "\n".join(lines)

    def to_json(self, indent: int = 2) -> str:
        """Export workflow as JSON.

        Args:
            indent: JSON indentation

        Returns:
            JSON string
        """
        workflow_dict = {
            "name": self.config.name,
            "description": self.config.description,
            "start_node": self.config.start_node,
            "max_iterations": self.config.max_iterations,
            "nodes": []
        }

        for node in self.config.nodes:
            node_dict = {
                "id": node.id,
                "type": node.type,
                "name": node.name,
                "agent_name": node.agent_name,
                "next_nodes": node.next_nodes,
                "metadata": node.metadata
            }
            workflow_dict["nodes"].append(node_dict)

        return json.dumps(workflow_dict, indent=indent)

    def print_summary(self):
        """Print workflow summary to console."""
        print(self.to_ascii())
        print()
        print("Mermaid Diagram:")
        print("-" * 60)
        print(self.to_mermaid())
        print()


class ExecutionTracer:
    """Trace and visualize workflow execution.

    Example:
        ```python
        from unify_llm.agent.visualization import ExecutionTracer

        tracer = ExecutionTracer()

        # Enable tracing
        tracer.start()

        # Run workflow
        result = workflow.run("input")

        # Stop and display trace
        tracer.stop()
        tracer.print_trace()
        ```
    """

    def __init__(self):
        """Initialize execution tracer."""
        self.traces: List[Dict[str, Any]] = []
        self.is_tracing = False

    def start(self):
        """Start tracing."""
        self.is_tracing = True
        self.traces = []

    def stop(self):
        """Stop tracing."""
        self.is_tracing = False

    def add_trace(
        self,
        node_id: str,
        node_name: str,
        input_data: str,
        output_data: str,
        success: bool,
        duration: float = 0.0
    ):
        """Add a trace entry.

        Args:
            node_id: Node ID
            node_name: Node name
            input_data: Input to the node
            output_data: Output from the node
            success: Whether execution succeeded
            duration: Execution duration in seconds
        """
        if self.is_tracing:
            self.traces.append({
                "node_id": node_id,
                "node_name": node_name,
                "input": input_data[:200],
                "output": output_data[:200],
                "success": success,
                "duration": duration
            })

    def print_trace(self):
        """Print execution trace."""
        print("Execution Trace:")
        print("=" * 80)

        for i, trace in enumerate(self.traces, 1):
            status = "✓" if trace["success"] else "✗"
            print(f"\n{i}. {status} {trace['node_name']} ({trace['node_id']})")
            print(f"   Duration: {trace['duration']:.2f}s")
            print(f"   Input: {trace['input']}...")
            print(f"   Output: {trace['output']}...")

        print()

    def to_json(self) -> str:
        """Export trace as JSON.

        Returns:
            JSON string
        """
        return json.dumps(self.traces, indent=2)


def visualize_workflow(workflow: Workflow, format: str = "ascii") -> str:
    """Quick function to visualize a workflow.

    Args:
        workflow: Workflow to visualize
        format: Output format (ascii, mermaid, json)

    Returns:
        Visualization string
    """
    viz = WorkflowVisualizer(workflow)

    if format == "ascii":
        return viz.to_ascii()
    elif format == "mermaid":
        return viz.to_mermaid()
    elif format == "json":
        return viz.to_json()
    else:
        raise ValueError(f"Unknown format: {format}")
