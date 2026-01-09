"""Agent-to-Agent communication implementation."""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel

from src.a2a.protocol import (
    A2ARequest,
    A2AResponse,
    AgentCapability,
    AgentInfo,
    AgentStatus,
    TaskRequest,
    TaskResponse,
)


class A2AAgentConfig(BaseModel):
    """Configuration for A2A agent."""
    agent_id: Optional[str] = None
    agent_name: str
    capabilities: List[AgentCapability] = []
    heartbeat_interval: int = 30  # seconds
    discovery_enabled: bool = True


class AgentRegistry:
    """Registry for tracking available agents."""

    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
        self._lock = asyncio.Lock()

    async def register(self, agent_info: AgentInfo) -> None:
        """Register an agent.

        Args:
            agent_info: Agent information
        """
        async with self._lock:
            self._agents[agent_info.agent_id] = agent_info

    async def unregister(self, agent_id: str) -> None:
        """Unregister an agent.

        Args:
            agent_id: Agent ID
        """
        async with self._lock:
            self._agents.pop(agent_id, None)

    async def update_status(self, agent_id: str, status: AgentStatus) -> None:
        """Update agent status.

        Args:
            agent_id: Agent ID
            status: New status
        """
        async with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].status = status
                self._agents[agent_id].last_seen = datetime.now()

    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent information.

        Args:
            agent_id: Agent ID

        Returns:
            Agent information or None
        """
        async with self._lock:
            return self._agents.get(agent_id)

    async def find_agents(
        self,
        capabilities: Optional[List[str]] = None,
        status: Optional[AgentStatus] = None
    ) -> List[AgentInfo]:
        """Find agents matching criteria.

        Args:
            capabilities: Required capabilities
            status: Required status

        Returns:
            List of matching agents
        """
        async with self._lock:
            agents = list(self._agents.values())

        # Filter by capabilities
        if capabilities:
            agents = [
                agent for agent in agents
                if any(cap.name in capabilities for cap in agent.capabilities)
            ]

        # Filter by status
        if status:
            agents = [agent for agent in agents if agent.status == status]

        return agents

    async def cleanup_stale(self, max_age: timedelta) -> None:
        """Remove stale agents.

        Args:
            max_age: Maximum age for agents
        """
        now = datetime.now()
        async with self._lock:
            stale_ids = [
                agent_id for agent_id, agent in self._agents.items()
                if now - agent.last_seen > max_age
            ]
            for agent_id in stale_ids:
                self._agents.pop(agent_id)


class AgentDiscovery:
    """Service for discovering other agents."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    async def discover(
        self,
        capabilities: Optional[List[str]] = None
    ) -> List[AgentInfo]:
        """Discover agents with specified capabilities.

        Args:
            capabilities: Required capabilities

        Returns:
            List of discovered agents
        """
        return await self.registry.find_agents(
            capabilities=capabilities,
            status=AgentStatus.IDLE
        )

    async def find_best_agent(
        self,
        capability: str,
        criteria: Optional[Callable[[AgentInfo], float]] = None
    ) -> Optional[AgentInfo]:
        """Find the best agent for a capability.

        Args:
            capability: Required capability
            criteria: Scoring function (higher is better)

        Returns:
            Best agent or None
        """
        agents = await self.discover(capabilities=[capability])
        if not agents:
            return None

        if criteria:
            agents.sort(key=criteria, reverse=True)

        return agents[0]


class A2AAgent:
    """Agent capable of A2A communication.

    This class wraps a standard UnifyLLM agent with A2A capabilities,
    allowing it to communicate and collaborate with other agents.

    Example:
        ```python
        from src import UnifyLLM
        from src.agent import Agent, AgentConfig
        from src.a2a import A2AAgent, A2AAgentConfig, AgentCapability

        # Create base agent
        client = UnifyLLM(provider="databricks", ...)
        base_agent = Agent(config=AgentConfig(...), client=client)

        # Wrap with A2A capabilities
        a2a_config = A2AAgentConfig(
            agent_name="math_agent",
            capabilities=[
                AgentCapability(
                    name="calculator",
                    description="Perform math calculations",
                    input_schema={...},
                    output_schema={...}
                )
            ]
        )
        a2a_agent = A2AAgent(base_agent, a2a_config)

        # Start A2A agent
        await a2a_agent.start()

        # Delegate task to another agent
        result = await a2a_agent.delegate_task(
            "other_agent_id",
            "capability_name",
            {"input": "data"}
        )
        ```
    """

    def __init__(
        self,
        base_agent: Any,
        config: A2AAgentConfig,
        registry: Optional[AgentRegistry] = None
    ):
        """Initialize A2A agent.

        Args:
            base_agent: Underlying agent implementation
            config: A2A configuration
            registry: Shared agent registry
        """
        self.base_agent = base_agent
        self.config = config
        self.agent_id = config.agent_id or str(uuid.uuid4())
        self.registry = registry or AgentRegistry()
        self.discovery = AgentDiscovery(self.registry)

        self._message_handlers: Dict[str, Callable] = {}
        self._capability_handlers: Dict[str, Callable] = {}
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None

    def handle_capability(self, capability_name: str):
        """Decorator to register a capability handler.

        Args:
            capability_name: Name of the capability

        Example:
            ```python
            @a2a_agent.handle_capability("calculator")
            async def handle_calculator(input_data: Dict) -> Dict:
                # Process calculation
                return {"result": ...}
            ```
        """
        def decorator(func: Callable):
            self._capability_handlers[capability_name] = func
            return func
        return decorator

    async def start(self) -> None:
        """Start the A2A agent."""
        # Register with registry
        agent_info = AgentInfo(
            agent_id=self.agent_id,
            agent_name=self.config.agent_name,
            capabilities=self.config.capabilities,
            status=AgentStatus.IDLE
        )
        await self.registry.register(agent_info)

        self._running = True

        # Start heartbeat
        if self.config.heartbeat_interval > 0:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        """Stop the A2A agent."""
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        await self.registry.unregister(self.agent_id)

    async def delegate_task(
        self,
        target_agent_id: str,
        capability: str,
        input_data: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> TaskResponse:
        """Delegate a task to another agent.

        Args:
            target_agent_id: ID of target agent
            capability: Required capability
            input_data: Task input data
            timeout: Task timeout in seconds

        Returns:
            Task response
        """
        task_id = str(uuid.uuid4())
        task_request = TaskRequest(
            task_id=task_id,
            capability=capability,
            input_data=input_data,
            timeout=timeout
        )

        # Send task request
        request = A2ARequest(
            id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            receiver_id=target_agent_id,
            method="execute_task",
            params=task_request.model_dump()
        )

        # Simulate sending and receiving (would use actual transport in production)
        response = await self._send_request(request)

        if response.error:
            return TaskResponse(
                task_id=task_id,
                success=False,
                error=response.error.get("message", "Unknown error")
            )

        return TaskResponse(**response.result)

    async def discover_agents(
        self,
        capabilities: Optional[List[str]] = None
    ) -> List[AgentInfo]:
        """Discover other agents.

        Args:
            capabilities: Required capabilities

        Returns:
            List of discovered agents
        """
        return await self.discovery.discover(capabilities)

    async def find_agent_for_task(
        self,
        capability: str
    ) -> Optional[AgentInfo]:
        """Find best agent for a specific task.

        Args:
            capability: Required capability

        Returns:
            Best agent or None
        """
        return await self.discovery.find_best_agent(capability)

    async def handle_request(self, request: A2ARequest) -> A2AResponse:
        """Handle an incoming request.

        Args:
            request: Incoming request

        Returns:
            Response
        """
        method = request.method

        if method == "execute_task":
            return await self._handle_execute_task(request)
        elif method in self._message_handlers:
            handler = self._message_handlers[method]
            result = await handler(request.params)
            return A2AResponse(
                id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                receiver_id=request.sender_id,
                request_id=request.id,
                result=result
            )
        else:
            return A2AResponse(
                id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                receiver_id=request.sender_id,
                request_id=request.id,
                error={"message": f"Unknown method: {method}"}
            )

    async def _handle_execute_task(self, request: A2ARequest) -> A2AResponse:
        """Handle task execution request."""
        task_req = TaskRequest(**request.params)

        # Update status to busy
        await self.registry.update_status(self.agent_id, AgentStatus.BUSY)

        try:
            # Execute task
            if task_req.capability in self._capability_handlers:
                handler = self._capability_handlers[task_req.capability]
                output = await handler(task_req.input_data)

                response = TaskResponse(
                    task_id=task_req.task_id,
                    success=True,
                    output_data=output
                )
            else:
                response = TaskResponse(
                    task_id=task_req.task_id,
                    success=False,
                    error=f"Capability not found: {task_req.capability}"
                )
        except Exception as e:
            response = TaskResponse(
                task_id=task_req.task_id,
                success=False,
                error=str(e)
            )
        finally:
            # Update status back to idle
            await self.registry.update_status(self.agent_id, AgentStatus.IDLE)

        return A2AResponse(
            id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            receiver_id=request.sender_id,
            request_id=request.id,
            result=response.model_dump()
        )

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats."""
        while self._running:
            try:
                await self.registry.update_status(self.agent_id, AgentStatus.IDLE)
                await asyncio.sleep(self.config.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Heartbeat error: {e}")

    async def _send_request(self, request: A2ARequest) -> A2AResponse:
        """Send a request and wait for response.

        In a real implementation, this would use a message bus or network transport.
        For now, it delegates to the actual agent's handle_request method.

        Args:
            request: Request to send

        Returns:
            Response
        """
        # Get target agent
        target_agent = await self.registry.get_agent(request.receiver_id)
        if not target_agent:
            return A2AResponse(
                id=str(uuid.uuid4()),
                sender_id="system",
                receiver_id=request.sender_id,
                request_id=request.id,
                error={"message": f"Agent not found: {request.receiver_id}"}
            )

        # For local agents in same registry, handle the request directly
        # In production, this would go through a message bus
        return await self.handle_request(request)
