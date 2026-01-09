"""Agent collaboration patterns and strategies."""

import asyncio
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.a2a.agent_comm import A2AAgent, AgentDiscovery
from src.a2a.protocol import AgentInfo, TaskResponse


class CollaborationStrategy(str, Enum):
    """Strategy for agent collaboration."""
    SEQUENTIAL = "sequential"  # Tasks executed in sequence
    PARALLEL = "parallel"  # Tasks executed in parallel
    CONSENSUS = "consensus"  # Multiple agents reach consensus
    HIERARCHICAL = "hierarchical"  # Leader coordinates workers
    AUCTION = "auction"  # Agents bid for tasks


class TaskDelegation:
    """Handles task delegation to best-suited agents.

    Example:
        ```python
        delegation = TaskDelegation(discovery_service)

        # Delegate with automatic agent selection
        result = await delegation.delegate_auto(
            capability="data_analysis",
            input_data={"dataset": "sales_data.csv"}
        )
        ```
    """

    def __init__(self, discovery: AgentDiscovery):
        """Initialize task delegation.

        Args:
            discovery: Agent discovery service
        """
        self.discovery = discovery

    async def delegate_auto(
        self,
        capability: str,
        input_data: Dict[str, Any],
        selection_criteria: Optional[Callable[[AgentInfo], float]] = None
    ) -> TaskResponse:
        """Automatically delegate task to best agent.

        Args:
            capability: Required capability
            input_data: Task input
            selection_criteria: Agent scoring function

        Returns:
            Task response
        """
        # Find best agent
        agent = await self.discovery.find_best_agent(capability, selection_criteria)

        if not agent:
            return TaskResponse(
                task_id="auto",
                success=False,
                error=f"No agent found with capability: {capability}"
            )

        # Delegate task (would use actual A2A communication)
        # This is a simplified version
        return TaskResponse(
            task_id="auto",
            success=True,
            output_data={"agent_id": agent.agent_id}
        )

    async def delegate_parallel(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[TaskResponse]:
        """Delegate multiple tasks in parallel.

        Args:
            tasks: List of task specifications

        Returns:
            List of task responses
        """
        coros = [
            self.delegate_auto(
                capability=task["capability"],
                input_data=task["input_data"]
            )
            for task in tasks
        ]

        return await asyncio.gather(*coros)


class ConsensusBuilder:
    """Build consensus among multiple agents.

    Example:
        ```python
        consensus = ConsensusBuilder(agents)

        # Get consensus on a decision
        decision = await consensus.reach_consensus(
            question="Should we approve this change?",
            voting_method="majority"
        )
        ```
    """

    def __init__(self, agents: List[A2AAgent]):
        """Initialize consensus builder.

        Args:
            agents: List of participating agents
        """
        self.agents = agents

    async def reach_consensus(
        self,
        task: str,
        input_data: Dict[str, Any],
        voting_method: str = "majority"
    ) -> Dict[str, Any]:
        """Reach consensus among agents.

        Args:
            task: Task description
            input_data: Task input
            voting_method: Voting method (majority, unanimous, weighted)

        Returns:
            Consensus result
        """
        # Collect responses from all agents
        responses = []
        for agent in self.agents:
            # Each agent processes the task
            # (simplified - would use actual task execution)
            response = {
                "agent_id": agent.agent_id,
                "vote": "approve",  # Placeholder
                "confidence": 0.8
            }
            responses.append(response)

        # Apply voting method
        if voting_method == "majority":
            votes = [r["vote"] for r in responses]
            decision = max(set(votes), key=votes.count)
        elif voting_method == "unanimous":
            votes = [r["vote"] for r in responses]
            decision = votes[0] if len(set(votes)) == 1 else "no_consensus"
        elif voting_method == "weighted":
            # Weight by confidence
            vote_weights: Dict[str, float] = {}
            for r in responses:
                vote = r["vote"]
                vote_weights[vote] = vote_weights.get(vote, 0) + r["confidence"]
            decision = max(vote_weights, key=vote_weights.get)
        else:
            decision = "unknown_method"

        return {
            "decision": decision,
            "responses": responses,
            "voting_method": voting_method
        }


class AgentCollaboration:
    """Orchestrates multi-agent collaboration.

    Example:
        ```python
        collab = AgentCollaboration(strategy=CollaborationStrategy.PARALLEL)

        # Add agents
        collab.add_agent(agent1)
        collab.add_agent(agent2)

        # Execute collaborative task
        result = await collab.execute({
            "task": "analyze_data",
            "data": {...}
        })
        ```
    """

    def __init__(
        self,
        strategy: CollaborationStrategy = CollaborationStrategy.SEQUENTIAL
    ):
        """Initialize collaboration orchestrator.

        Args:
            strategy: Collaboration strategy
        """
        self.strategy = strategy
        self.agents: List[A2AAgent] = []

    def add_agent(self, agent: A2AAgent) -> None:
        """Add an agent to the collaboration.

        Args:
            agent: Agent to add
        """
        self.agents.append(agent)

    async def execute(
        self,
        task_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a collaborative task.

        Args:
            task_spec: Task specification

        Returns:
            Execution result
        """
        if self.strategy == CollaborationStrategy.SEQUENTIAL:
            return await self._execute_sequential(task_spec)
        elif self.strategy == CollaborationStrategy.PARALLEL:
            return await self._execute_parallel(task_spec)
        elif self.strategy == CollaborationStrategy.CONSENSUS:
            return await self._execute_consensus(task_spec)
        else:
            raise ValueError(f"Unsupported strategy: {self.strategy}")

    async def _execute_sequential(
        self,
        task_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tasks sequentially."""
        results = []
        current_input = task_spec.get("data", {})

        for agent in self.agents:
            # Execute task on agent
            # (simplified - would use actual A2A communication)
            result = {
                "agent_id": agent.agent_id,
                "output": current_input  # Placeholder
            }
            results.append(result)
            current_input = result["output"]

        return {
            "strategy": "sequential",
            "results": results,
            "final_output": current_input
        }

    async def _execute_parallel(
        self,
        task_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tasks in parallel."""
        coros = []
        for agent in self.agents:
            # Create task for each agent
            async def agent_task(a):
                # Simplified execution
                return {
                    "agent_id": a.agent_id,
                    "output": task_spec.get("data", {})
                }

            coros.append(agent_task(agent))

        results = await asyncio.gather(*coros)

        return {
            "strategy": "parallel",
            "results": results
        }

    async def _execute_consensus(
        self,
        task_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute with consensus building."""
        consensus_builder = ConsensusBuilder(self.agents)
        result = await consensus_builder.reach_consensus(
            task=task_spec.get("task", ""),
            input_data=task_spec.get("data", {}),
            voting_method=task_spec.get("voting_method", "majority")
        )

        return {
            "strategy": "consensus",
            **result
        }
