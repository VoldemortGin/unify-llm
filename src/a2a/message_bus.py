"""
A2A Message Bus - Distributed Agent Communication

This module provides a message bus for agent-to-agent communication,
enabling distributed agents to communicate across processes or networks.
"""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel


class MessageBusConfig(BaseModel):
    """Configuration for message bus."""
    name: str = "default"
    max_queue_size: int = 1000
    message_ttl: int = 60  # seconds
    enable_logging: bool = True


class MessageBus:
    """Message bus for agent-to-agent communication.

    Provides publish-subscribe and request-response patterns for
    distributed agent communication.

    Example:
        ```python
        # Create message bus
        bus = MessageBus(MessageBusConfig(name="main-bus"))

        # Subscribe to agent messages
        async def handle_message(msg):
            print(f"Received: {msg}")

        bus.subscribe("agent1", handle_message)

        # Publish message
        await bus.publish("agent1", {"type": "task", "data": "..."})

        # Request-response
        response = await bus.request("agent2", {"method": "solve", "params": {...}})
        ```
    """

    def __init__(self, config: MessageBusConfig):
        """Initialize message bus.

        Args:
            config: Message bus configuration
        """
        self.config = config
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._queues: Dict[str, asyncio.Queue] = {}
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._running = False
        self._stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0
        }

    async def start(self) -> None:
        """Start the message bus."""
        self._running = True
        if self.config.enable_logging:
            print(f"✅ Message bus '{self.config.name}' started")

    async def stop(self) -> None:
        """Stop the message bus."""
        self._running = False
        # Clear all queues
        for queue in self._queues.values():
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

        if self.config.enable_logging:
            print(f"🛑 Message bus '{self.config.name}' stopped")
            print(f"   Stats: {self._stats}")

    def subscribe(self, agent_id: str, handler: Callable) -> None:
        """Subscribe to messages for an agent.

        Args:
            agent_id: Agent ID to subscribe to
            handler: Async function to handle messages
        """
        self._subscribers[agent_id].append(handler)

        # Create queue if not exists
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue(maxsize=self.config.max_queue_size)

        if self.config.enable_logging:
            print(f"📨 Subscribed: {agent_id} ({len(self._subscribers[agent_id])} handlers)")

    def unsubscribe(self, agent_id: str, handler: Optional[Callable] = None) -> None:
        """Unsubscribe from messages.

        Args:
            agent_id: Agent ID
            handler: Specific handler to remove, or None to remove all
        """
        if handler:
            if agent_id in self._subscribers:
                self._subscribers[agent_id].remove(handler)
        else:
            self._subscribers.pop(agent_id, None)
            self._queues.pop(agent_id, None)

    async def publish(
        self,
        target_id: str,
        message: Dict[str, Any],
        sender_id: Optional[str] = None
    ) -> None:
        """Publish a message to a target agent.

        Args:
            target_id: Target agent ID
            message: Message to send
            sender_id: Sender agent ID
        """
        if not self._running:
            raise RuntimeError("Message bus is not running")

        # Add metadata
        full_message = {
            **message,
            "_target": target_id,
            "_sender": sender_id,
            "_timestamp": datetime.now().isoformat(),
            "_bus": self.config.name
        }

        # Add to queue
        if target_id in self._queues:
            try:
                await self._queues[target_id].put(full_message)
                self._stats["messages_sent"] += 1

                # Notify subscribers
                if target_id in self._subscribers:
                    for handler in self._subscribers[target_id]:
                        try:
                            await handler(full_message)
                        except Exception as e:
                            self._stats["errors"] += 1
                            if self.config.enable_logging:
                                print(f"❌ Handler error: {e}")
            except asyncio.QueueFull:
                self._stats["errors"] += 1
                if self.config.enable_logging:
                    print(f"⚠️  Queue full for agent: {target_id}")
        else:
            self._stats["errors"] += 1
            if self.config.enable_logging:
                print(f"⚠️  No queue for agent: {target_id}")

    async def broadcast(
        self,
        message: Dict[str, Any],
        sender_id: Optional[str] = None,
        exclude: Optional[Set[str]] = None
    ) -> None:
        """Broadcast message to all subscribers.

        Args:
            message: Message to broadcast
            sender_id: Sender agent ID
            exclude: Set of agent IDs to exclude
        """
        exclude = exclude or set()
        tasks = []

        for agent_id in self._queues.keys():
            if agent_id not in exclude:
                tasks.append(self.publish(agent_id, message, sender_id))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def request(
        self,
        target_id: str,
        request: Dict[str, Any],
        sender_id: Optional[str] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Send a request and wait for response.

        Args:
            target_id: Target agent ID
            request: Request message
            sender_id: Sender agent ID
            timeout: Response timeout in seconds

        Returns:
            Response message
        """
        request_id = f"req_{datetime.now().timestamp()}"

        # Create future for response
        future = asyncio.Future()
        self._pending_responses[request_id] = future

        # Send request
        request_msg = {
            **request,
            "_request_id": request_id,
            "_expects_response": True
        }
        await self.publish(target_id, request_msg, sender_id)

        try:
            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError as err:
            raise TimeoutError(f"Request timeout: {request_id}") from err
        finally:
            self._pending_responses.pop(request_id, None)

    async def respond(
        self,
        request_id: str,
        response: Dict[str, Any]
    ) -> None:
        """Send a response to a previous request.

        Args:
            request_id: Request ID to respond to
            response: Response message
        """
        if request_id in self._pending_responses:
            future = self._pending_responses[request_id]
            if not future.done():
                future.set_result(response)

    async def get_message(self, agent_id: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Get next message for an agent.

        Args:
            agent_id: Agent ID
            timeout: Wait timeout in seconds

        Returns:
            Message

        Raises:
            asyncio.TimeoutError: If timeout exceeded
            KeyError: If agent not subscribed
        """
        if agent_id not in self._queues:
            raise KeyError(f"Agent not subscribed: {agent_id}")

        queue = self._queues[agent_id]

        if timeout:
            message = await asyncio.wait_for(queue.get(), timeout=timeout)
        else:
            message = await queue.get()

        self._stats["messages_received"] += 1
        return message

    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics.

        Returns:
            Statistics dictionary
        """
        return {
            **self._stats,
            "subscribers": len(self._subscribers),
            "queues": len(self._queues),
            "pending_responses": len(self._pending_responses)
        }

    def get_subscribers(self) -> List[str]:
        """Get list of subscriber agent IDs.

        Returns:
            List of agent IDs
        """
        return list(self._queues.keys())


class DistributedMessageBus(MessageBus):
    """Message bus with network distribution support.

    Extends MessageBus to support distributed agents across network.
    """

    def __init__(self, config: MessageBusConfig, redis_url: Optional[str] = None):
        """Initialize distributed message bus.

        Args:
            config: Message bus configuration
            redis_url: Redis connection URL for distribution (optional)
        """
        super().__init__(config)
        self.redis_url = redis_url
        self._redis = None

    async def start(self) -> None:
        """Start distributed message bus."""
        await super().start()

        if self.redis_url:
            # In production, connect to Redis
            # For now, this is a placeholder
            if self.config.enable_logging:
                print(f"🌐 Distributed mode: {self.redis_url}")

    async def publish_remote(
        self,
        target_id: str,
        message: Dict[str, Any],
        sender_id: Optional[str] = None
    ) -> None:
        """Publish message to remote agent.

        Args:
            target_id: Target agent ID
            message: Message to send
            sender_id: Sender agent ID
        """
        # In production, publish to Redis/message queue
        # For now, use local publish
        await self.publish(target_id, message, sender_id)
