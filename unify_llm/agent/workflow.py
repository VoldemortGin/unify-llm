"""Workflow orchestration for multi-agent systems."""

from typing import Any, Callable, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
import logging

from unify_llm.agent.base import Agent
from unify_llm.agent.executor import AgentExecutor, ExecutionResult
from unify_llm.agent.memory import SharedMemory

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """Types of workflow nodes."""
    AGENT = "agent"  # Agent execution node
    CONDITION = "condition"  # Conditional branching
    PARALLEL = "parallel"  # Parallel execution
    SEQUENTIAL = "sequential"  # Sequential execution
    HUMAN_IN_LOOP = "human_in_loop"  # Human approval/input required


class WorkflowNode(BaseModel):
    """A node in the workflow.

    Attributes:
        id: Unique node identifier
        type: Node type
        name: Human-readable name
        agent_name: Name of agent to execute (for AGENT nodes)
        condition: Condition function (for CONDITION nodes)
        next_nodes: Next nodes to execute
        parallel_nodes: Nodes to execute in parallel (for PARALLEL nodes)
        metadata: Additional metadata
    """

    id: str = Field(..., description="Unique node ID")
    type: NodeType = Field(..., description="Node type")
    name: str = Field(..., description="Node name")
    agent_name: Optional[str] = Field(default=None, description="Agent name for AGENT nodes")
    condition: Optional[Callable] = Field(
        default=None,
        description="Condition function for CONDITION nodes"
    )
    next_nodes: List[str] = Field(default_factory=list, description="Next node IDs")
    parallel_nodes: List[str] = Field(
        default_factory=list,
        description="Parallel node IDs for PARALLEL nodes"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        arbitrary_types_allowed = True


class WorkflowConfig(BaseModel):
    """Configuration for a workflow.

    Attributes:
        name: Workflow name
        description: Workflow description
        start_node: ID of the starting node
        nodes: List of workflow nodes
        max_iterations: Maximum workflow iterations
        enable_shared_memory: Whether to use shared memory
    """

    name: str = Field(..., description="Workflow name")
    description: str = Field(default="", description="Workflow description")
    start_node: str = Field(..., description="Starting node ID")
    nodes: List[WorkflowNode] = Field(default_factory=list, description="Workflow nodes")
    max_iterations: int = Field(default=50, ge=1, description="Maximum iterations")
    enable_shared_memory: bool = Field(
        default=True,
        description="Enable shared memory across agents"
    )


class WorkflowResult(BaseModel):
    """Result from workflow execution.

    Attributes:
        success: Whether workflow succeeded
        output: Final workflow output
        node_results: Results from each node
        iterations: Number of iterations
        error: Error message if failed
    """

    success: bool = Field(..., description="Execution success")
    output: Any = Field(default=None, description="Final output")
    node_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Results from each node"
    )
    iterations: int = Field(default=0, description="Number of iterations")
    error: Optional[str] = Field(default=None, description="Error message")


class Workflow:
    """Orchestrates multi-agent workflows.

    Supports:
    - Sequential agent execution
    - Parallel agent execution
    - Conditional branching
    - Human-in-the-loop approvals
    - Shared memory across agents

    Example:
        ```python
        from unify_llm import UnifyLLM
        from unify_llm.agent import (
            Agent, AgentConfig, AgentExecutor,
            Workflow, WorkflowConfig, WorkflowNode, NodeType
        )

        # Create agents
        researcher = Agent(config=AgentConfig(
            name="researcher",
            model="gpt-4",
            provider="openai",
            system_prompt="You research topics thoroughly."
        ), client=client)

        writer = Agent(config=AgentConfig(
            name="writer",
            model="gpt-4",
            provider="openai",
            system_prompt="You write clear summaries."
        ), client=client)

        # Create workflow
        workflow_config = WorkflowConfig(
            name="research_and_write",
            description="Research a topic and write a summary",
            start_node="research",
            nodes=[
                WorkflowNode(
                    id="research",
                    type=NodeType.AGENT,
                    name="Research Topic",
                    agent_name="researcher",
                    next_nodes=["write"]
                ),
                WorkflowNode(
                    id="write",
                    type=NodeType.AGENT,
                    name="Write Summary",
                    agent_name="writer",
                    next_nodes=[]
                )
            ]
        )

        # Create and run workflow
        workflow = Workflow(
            config=workflow_config,
            agents={"researcher": researcher, "writer": writer}
        )

        result = workflow.run("Explain quantum computing")
        print(result.output)
        ```
    """

    def __init__(
            self,
            config: WorkflowConfig,
            agents: Dict[str, Agent],
            tool_registry: Optional[Any] = None,
            shared_memory: Optional[SharedMemory] = None,
            human_input_handler: Optional[Callable[[str], str]] = None,
            verbose: bool = False
    ):
        """Initialize the workflow.

        Args:
            config: Workflow configuration
            agents: Dictionary of agents by name
            tool_registry: Shared tool registry for all agents
            shared_memory: Shared memory instance
            human_input_handler: Function to get human input
            verbose: Whether to log execution details
        """
        self.config = config
        self.agents = agents
        self.tool_registry = tool_registry
        self.shared_memory = shared_memory or (
            SharedMemory() if config.enable_shared_memory else None
        )
        self.human_input_handler = human_input_handler
        self.verbose = verbose

        # Create executors for each agent
        self.executors: Dict[str, AgentExecutor] = {}
        for agent_name, agent in agents.items():
            self.executors[agent_name] = AgentExecutor(
                agent=agent,
                tool_registry=tool_registry,
                verbose=verbose
            )

        # Build node lookup
        self.nodes: Dict[str, WorkflowNode] = {
            node.id: node for node in config.nodes
        }

    def run(self, user_input: str, **kwargs) -> WorkflowResult:
        """Run the workflow synchronously.

        Args:
            user_input: Initial user input
            **kwargs: Additional parameters

        Returns:
            Workflow result
        """
        try:
            if self.verbose:
                logger.info(f"Starting workflow: {self.config.name}")

            # Initialize shared memory with user input
            if self.shared_memory:
                self.shared_memory.set("user_input", user_input)
                self.shared_memory.set("current_output", user_input)

            node_results = {}
            current_node_id = self.config.start_node
            iterations = 0

            while current_node_id and iterations < self.config.max_iterations:
                iterations += 1

                if self.verbose:
                    logger.info(f"Iteration {iterations}: Executing node {current_node_id}")

                # Get current node
                node = self.nodes.get(current_node_id)
                if not node:
                    return WorkflowResult(
                        success=False,
                        node_results=node_results,
                        iterations=iterations,
                        error=f"Node '{current_node_id}' not found"
                    )

                # Execute node
                result = self._execute_node(node, node_results, **kwargs)
                node_results[node.id] = result

                # Determine next node
                current_node_id = self._get_next_node(node, result)

            # Get final output
            final_output = self.shared_memory.get("current_output") if self.shared_memory else None

            return WorkflowResult(
                success=True,
                output=final_output,
                node_results=node_results,
                iterations=iterations
            )

        except Exception as e:
            logger.error(f"Error executing workflow: {e}", exc_info=True)
            return WorkflowResult(
                success=False,
                node_results=node_results if 'node_results' in locals() else {},
                iterations=iterations if 'iterations' in locals() else 0,
                error=str(e)
            )

    async def arun(self, user_input: str, **kwargs) -> WorkflowResult:
        """Run the workflow asynchronously.

        Args:
            user_input: Initial user input
            **kwargs: Additional parameters

        Returns:
            Workflow result
        """
        try:
            if self.verbose:
                logger.info(f"Starting workflow: {self.config.name}")

            # Initialize shared memory with user input
            if self.shared_memory:
                self.shared_memory.set("user_input", user_input)
                self.shared_memory.set("current_output", user_input)

            node_results = {}
            current_node_id = self.config.start_node
            iterations = 0

            while current_node_id and iterations < self.config.max_iterations:
                iterations += 1

                if self.verbose:
                    logger.info(f"Iteration {iterations}: Executing node {current_node_id}")

                # Get current node
                node = self.nodes.get(current_node_id)
                if not node:
                    return WorkflowResult(
                        success=False,
                        node_results=node_results,
                        iterations=iterations,
                        error=f"Node '{current_node_id}' not found"
                    )

                # Execute node
                result = await self._aexecute_node(node, node_results, **kwargs)
                node_results[node.id] = result

                # Determine next node
                current_node_id = self._get_next_node(node, result)

            # Get final output
            final_output = self.shared_memory.get("current_output") if self.shared_memory else None

            return WorkflowResult(
                success=True,
                output=final_output,
                node_results=node_results,
                iterations=iterations
            )

        except Exception as e:
            logger.error(f"Error executing workflow: {e}", exc_info=True)
            return WorkflowResult(
                success=False,
                node_results=node_results if 'node_results' in locals() else {},
                iterations=iterations if 'iterations' in locals() else 0,
                error=str(e)
            )

    def _execute_node(
            self,
            node: WorkflowNode,
            node_results: Dict[str, Any],
            **kwargs
    ) -> Any:
        """Execute a workflow node synchronously.

        Args:
            node: Node to execute
            node_results: Results from previous nodes
            **kwargs: Additional parameters

        Returns:
            Node execution result
        """
        if node.type == NodeType.AGENT:
            return self._execute_agent_node(node, **kwargs)
        elif node.type == NodeType.CONDITION:
            return self._execute_condition_node(node, node_results)
        elif node.type == NodeType.HUMAN_IN_LOOP:
            return self._execute_human_in_loop_node(node)
        else:
            return {"success": True, "message": f"Node type {node.type} executed"}

    async def _aexecute_node(
            self,
            node: WorkflowNode,
            node_results: Dict[str, Any],
            **kwargs
    ) -> Any:
        """Execute a workflow node asynchronously.

        Args:
            node: Node to execute
            node_results: Results from previous nodes
            **kwargs: Additional parameters

        Returns:
            Node execution result
        """
        if node.type == NodeType.AGENT:
            return await self._aexecute_agent_node(node, **kwargs)
        elif node.type == NodeType.CONDITION:
            return self._execute_condition_node(node, node_results)
        elif node.type == NodeType.HUMAN_IN_LOOP:
            return self._execute_human_in_loop_node(node)
        else:
            return {"success": True, "message": f"Node type {node.type} executed"}

    def _execute_agent_node(self, node: WorkflowNode, **kwargs) -> ExecutionResult:
        """Execute an agent node.

        Args:
            node: Agent node
            **kwargs: Additional parameters

        Returns:
            Agent execution result
        """
        if not node.agent_name or node.agent_name not in self.executors:
            return ExecutionResult(
                success=False,
                error=f"Agent '{node.agent_name}' not found"
            )

        executor = self.executors[node.agent_name]

        # Get input from shared memory
        user_input = self.shared_memory.get("current_output") if self.shared_memory else ""

        # Execute agent
        result = executor.run(user_input, **kwargs)

        # Update shared memory with output
        if self.shared_memory and result.success:
            self.shared_memory.set("current_output", result.output)

        return result

    async def _aexecute_agent_node(self, node: WorkflowNode, **kwargs) -> ExecutionResult:
        """Execute an agent node asynchronously.

        Args:
            node: Agent node
            **kwargs: Additional parameters

        Returns:
            Agent execution result
        """
        if not node.agent_name or node.agent_name not in self.executors:
            return ExecutionResult(
                success=False,
                error=f"Agent '{node.agent_name}' not found"
            )

        executor = self.executors[node.agent_name]

        # Get input from shared memory
        user_input = self.shared_memory.get("current_output") if self.shared_memory else ""

        # Execute agent
        result = await executor.arun(user_input, **kwargs)

        # Update shared memory with output
        if self.shared_memory and result.success:
            self.shared_memory.set("current_output", result.output)

        return result

    def _execute_condition_node(
            self,
            node: WorkflowNode,
            node_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a condition node.

        Args:
            node: Condition node
            node_results: Results from previous nodes

        Returns:
            Condition result
        """
        if not node.condition:
            return {"success": False, "error": "No condition function provided"}

        try:
            # Evaluate condition
            condition_result = node.condition(node_results, self.shared_memory)
            return {
                "success": True,
                "condition_met": condition_result
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Condition evaluation error: {str(e)}"
            }

    def _execute_human_in_loop_node(self, node: WorkflowNode) -> Dict[str, Any]:
        """Execute a human-in-the-loop node.

        Args:
            node: Human-in-loop node

        Returns:
            Human input result
        """
        if not self.human_input_handler:
            return {
                "success": False,
                "error": "No human input handler configured"
            }

        try:
            # Get current state for human review
            current_output = self.shared_memory.get("current_output") if self.shared_memory else ""

            # Get human input
            human_input = self.human_input_handler(
                f"Node '{node.name}' requires input. Current state: {current_output}"
            )

            # Update shared memory
            if self.shared_memory:
                self.shared_memory.set("current_output", human_input)

            return {
                "success": True,
                "human_input": human_input
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Human input error: {str(e)}"
            }

    def _get_next_node(self, node: WorkflowNode, result: Any) -> Optional[str]:
        """Determine the next node to execute.

        Args:
            node: Current node
            result: Current node's result

        Returns:
            Next node ID or None
        """
        if node.type == NodeType.CONDITION:
            # For condition nodes, check the condition result
            if isinstance(result, dict) and result.get("condition_met"):
                return node.next_nodes[0] if node.next_nodes else None
            else:
                return node.next_nodes[1] if len(node.next_nodes) > 1 else None
        else:
            # For other nodes, just take the first next node
            return node.next_nodes[0] if node.next_nodes else None
