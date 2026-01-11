"""Performance monitoring and metrics for AI agents."""


from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class AgentMetrics:
    """Metrics for agent execution.

    Attributes:
        agent_name: Name of the agent
        total_executions: Total number of executions
        successful_executions: Number of successful executions
        failed_executions: Number of failed executions
        total_duration: Total execution time in seconds
        avg_duration: Average execution time
        total_iterations: Total iterations across all executions
        avg_iterations: Average iterations per execution
        total_tool_calls: Total tool calls made
        avg_tool_calls: Average tool calls per execution
        tool_usage: Count of each tool used
    """
    agent_name: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    total_iterations: int = 0
    avg_iterations: float = 0.0
    total_tool_calls: int = 0
    avg_tool_calls: float = 0.0
    tool_usage: dict[str, int] = field(default_factory=dict)

    def update_averages(self) -> None:
        """Update average metrics."""
        if self.total_executions > 0:
            self.avg_duration = self.total_duration / self.total_executions
            self.avg_iterations = self.total_iterations / self.total_executions
            self.avg_tool_calls = self.total_tool_calls / self.total_executions


class PerformanceMonitor:
    """Monitor and track agent performance.

    Example:
        ```python
        from unify_llm.agent.monitoring import PerformanceMonitor

        monitor = PerformanceMonitor()

        # Start monitoring an execution
        with monitor.track("my_agent"):
            result = executor.run("task")

        # Record the result
        monitor.record_result("my_agent", result)

        # Get metrics
        metrics = monitor.get_metrics("my_agent")
        print(f"Success rate: {metrics.successful_executions / metrics.total_executions}")

        # Print summary
        monitor.print_summary()
        ```
    """

    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: dict[str, AgentMetrics] = {}
        self._start_times: dict[str, float] = {}

    def start_execution(self, agent_name: str):
        """Start tracking an execution.

        Args:
            agent_name: Name of the agent
        """
        self._start_times[agent_name] = time.time()

        if agent_name not in self.metrics:
            self.metrics[agent_name] = AgentMetrics(agent_name=agent_name)

    def end_execution(
        self,
        agent_name: str,
        success: bool,
        iterations: int = 0,
        tool_calls: list[Dict] | None = None
    ):
        """End tracking an execution.

        Args:
            agent_name: Name of the agent
            success: Whether execution succeeded
            iterations: Number of iterations
            tool_calls: List of tool calls made
        """
        if agent_name not in self._start_times:
            return

        duration = time.time() - self._start_times[agent_name]
        del self._start_times[agent_name]

        metrics = self.metrics[agent_name]
        metrics.total_executions += 1
        metrics.total_duration += duration
        metrics.total_iterations += iterations

        if success:
            metrics.successful_executions += 1
        else:
            metrics.failed_executions += 1

        # Track tool usage
        if tool_calls:
            metrics.total_tool_calls += len(tool_calls)
            for call in tool_calls:
                tool_name = call.get("tool", "unknown")
                metrics.tool_usage[tool_name] = metrics.tool_usage.get(tool_name, 0) + 1

        metrics.update_averages()

    def track(self, agent_name: str):
        """Context manager for tracking execution.

        Args:
            agent_name: Name of the agent

        Returns:
            Context manager
        """
        class ExecutionContext:
            def __init__(self, monitor, agent_name):
                self.monitor = monitor
                self.agent_name = agent_name

            def __enter__(self):
                self.monitor.start_execution(self.agent_name)
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                # Record as failed if exception occurred
                success = exc_type is None
                self.monitor.end_execution(self.agent_name, success=success)
                return False

        return ExecutionContext(self, agent_name)

    def record_result(self, agent_name: str, result: Any):
        """Record execution result.

        Args:
            agent_name: Name of the agent
            result: Execution result object
        """
        if hasattr(result, 'success') and hasattr(result, 'iterations'):
            tool_calls = getattr(result, 'tool_calls', [])
            self.end_execution(
                agent_name,
                success=result.success,
                iterations=result.iterations,
                tool_calls=tool_calls
            )

    def get_metrics(self, agent_name: str) -> AgentMetrics | None:
        """Get metrics for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent metrics or None
        """
        return self.metrics.get(agent_name)

    def get_all_metrics(self) -> dict[str, AgentMetrics]:
        """Get metrics for all agents.

        Returns:
            Dictionary of agent metrics
        """
        return self.metrics.copy()

    def print_summary(self, agent_name: str | None = None):
        """Print performance summary.

        Args:
            agent_name: Specific agent to print, or None for all
        """
        if agent_name:
            metrics = self.metrics.get(agent_name)
            if metrics:
                self._print_agent_metrics(metrics)
            else:
                print(f"No metrics found for agent: {agent_name}")
        else:
            print("=" * 80)
            print("Agent Performance Summary")
            print("=" * 80)
            print()

            for _agent_name, metrics in self.metrics.items():
                self._print_agent_metrics(metrics)
                print()

    def _print_agent_metrics(self, metrics: AgentMetrics):
        """Print metrics for a single agent.

        Args:
            metrics: Agent metrics to print
        """
        success_rate = (
            metrics.successful_executions / metrics.total_executions * 100
            if metrics.total_executions > 0 else 0
        )

        print(f"Agent: {metrics.agent_name}")
        print("-" * 80)
        print(f"Total Executions:      {metrics.total_executions}")
        print(f"Successful:            {metrics.successful_executions}")
        print(f"Failed:                {metrics.failed_executions}")
        print(f"Success Rate:          {success_rate:.1f}%")
        print(f"Avg Duration:          {metrics.avg_duration:.2f}s")
        print(f"Avg Iterations:        {metrics.avg_iterations:.1f}")
        print(f"Avg Tool Calls:        {metrics.avg_tool_calls:.1f}")

        if metrics.tool_usage:
            print("Tool Usage:")
            for tool, count in sorted(
                metrics.tool_usage.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                print(f"  - {tool}: {count}")

    def export_metrics(self, filepath: str):
        """Export metrics to JSON file.

        Args:
            filepath: Path to export file
        """
        data = {
            agent_name: asdict(metrics)
            for agent_name, metrics in self.metrics.items()
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def reset(self, agent_name: str | None = None):
        """Reset metrics.

        Args:
            agent_name: Specific agent to reset, or None for all
        """
        if agent_name:
            if agent_name in self.metrics:
                del self.metrics[agent_name]
        else:
            self.metrics.clear()


class ExecutionLogger:
    """Log agent executions for debugging and analysis.

    Example:
        ```python
        from unify_llm.agent.monitoring import ExecutionLogger

        logger = ExecutionLogger()

        # Log execution
        logger.log_execution(
            agent_name="assistant",
            user_input="What is 2+2?",
            result=result
        )

        # Get execution history
        history = logger.get_history("assistant")

        # Export logs
        logger.export_logs("execution_logs.json")
        ```
    """

    def __init__(self, max_entries: int = 1000):
        """Initialize execution logger.

        Args:
            max_entries: Maximum number of log entries to keep
        """
        self.max_entries = max_entries
        self.logs: list[dict[str, Any]] = []

    def log_execution(
        self,
        agent_name: str,
        user_input: str,
        result: Any,
        metadata: Dict | None = None
    ):
        """Log an execution.

        Args:
            agent_name: Name of the agent
            user_input: User input
            result: Execution result
            metadata: Additional metadata
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_name": agent_name,
            "user_input": user_input[:500],  # Limit length
            "success": getattr(result, 'success', False),
            "output": getattr(result, 'output', '')[:500],
            "iterations": getattr(result, 'iterations', 0),
            "tool_calls": len(getattr(result, 'tool_calls', [])),
            "error": getattr(result, 'error', None),
            "metadata": metadata or {}
        }

        self.logs.append(log_entry)

        # Keep only recent entries
        if len(self.logs) > self.max_entries:
            self.logs = self.logs[-self.max_entries:]

    def get_history(
        self,
        agent_name: str | None = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get execution history.

        Args:
            agent_name: Filter by agent name, or None for all
            limit: Maximum number of entries to return

        Returns:
            List of log entries
        """
        if agent_name:
            filtered = [
                log for log in self.logs
                if log["agent_name"] == agent_name
            ]
        else:
            filtered = self.logs

        return filtered[-limit:]

    def get_failed_executions(self, agent_name: str | None = None) -> list[Dict]:
        """Get failed executions.

        Args:
            agent_name: Filter by agent name, or None for all

        Returns:
            List of failed execution logs
        """
        logs = self.get_history(agent_name)
        return [log for log in logs if not log["success"]]

    def export_logs(self, filepath: str):
        """Export logs to JSON file.

        Args:
            filepath: Path to export file
        """
        with open(filepath, 'w') as f:
            json.dump(self.logs, f, indent=2)

    def clear(self):
        """Clear all logs."""
        self.logs.clear()


# Global instances for convenience
_global_monitor = PerformanceMonitor()
_global_logger = ExecutionLogger()


def get_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    return _global_monitor


def get_logger() -> ExecutionLogger:
    """Get global execution logger instance."""
    return _global_logger
