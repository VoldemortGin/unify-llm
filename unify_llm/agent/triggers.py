"""Trigger system for workflow automation (n8n-style).

This module provides various triggers to start workflow executions automatically:
- Schedule triggers (cron-based)
- Webhook triggers (HTTP endpoints)
- Manual triggers
- Event triggers
"""


from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict

from croniter import croniter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TriggerType(str, Enum):
    """Types of workflow triggers."""
    MANUAL = "manual"  # Manual execution
    SCHEDULE = "schedule"  # Time-based (cron)
    WEBHOOK = "webhook"  # HTTP webhook
    EVENT = "event"  # Event-based
    INTERVAL = "interval"  # Fixed interval


class TriggerStatus(str, Enum):
    """Trigger execution status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    RUNNING = "running"
    ERROR = "error"


class TriggerEvent(BaseModel):
    """Event data from a trigger.

    Attributes:
        trigger_id: Unique trigger identifier
        trigger_type: Type of trigger
        timestamp: When the trigger fired
        data: Event payload data
        metadata: Additional metadata
    """

    trigger_id: str = Field(..., description="Trigger ID")
    trigger_type: TriggerType = Field(..., description="Trigger type")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")
    data: dict[str, Any] = Field(default_factory=dict, description="Event data")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Event metadata")


class TriggerConfig(BaseModel):
    """Configuration for a trigger.

    Attributes:
        id: Unique trigger ID
        name: Human-readable name
        type: Trigger type
        enabled: Whether trigger is active
        workflow_id: Associated workflow ID
        config: Type-specific configuration
    """

    id: str = Field(..., description="Trigger ID")
    name: str = Field(..., description="Trigger name")
    type: TriggerType = Field(..., description="Trigger type")
    enabled: bool = Field(default=True, description="Whether active")
    workflow_id: str = Field(..., description="Workflow to trigger")
    config: dict[str, Any] = Field(default_factory=dict, description="Trigger config")


class BaseTrigger:
    """Base class for all triggers.

    Example:
        ```python
        from unify_llm.agent.triggers import BaseTrigger, TriggerEvent

        class CustomTrigger(BaseTrigger):
            async def start(self):
                # Start monitoring
                pass

            async def stop(self):
                # Stop monitoring
                pass
        ```
    """

    def __init__(self, config: TriggerConfig, callback: Callable[[TriggerEvent], None]):
        """Initialize trigger.

        Args:
            config: Trigger configuration
            callback: Function to call when trigger fires
        """
        self.config = config
        self.callback = callback
        self.status = TriggerStatus.INACTIVE
        self._running = False

    async def start(self) -> None:
        """Start the trigger. Override in subclasses."""
        raise NotImplementedError

    async def stop(self) -> None:
        """Stop the trigger. Override in subclasses."""
        raise NotImplementedError

    def _fire(self, data: dict[str, Any] = None) -> None:
        """Fire the trigger and execute callback.

        Args:
            data: Event data
        """
        event = TriggerEvent(
            trigger_id=self.config.id,
            trigger_type=self.config.type,
            data=data or {},
            metadata={"workflow_id": self.config.workflow_id}
        )

        try:
            self.callback(event)
        except Exception as e:
            logger.error(f"Error in trigger callback: {e}")
            self.status = TriggerStatus.ERROR


class ScheduleTrigger(BaseTrigger):
    """Cron-based schedule trigger (like n8n Schedule Trigger).

    Example:
        ```python
        from unify_llm.agent.triggers import ScheduleTrigger, TriggerConfig, TriggerType

        def on_trigger(event):
            print(f"Scheduled execution: {event.timestamp}")

        config = TriggerConfig(
            id="schedule_1",
            name="Daily Report",
            type=TriggerType.SCHEDULE,
            workflow_id="workflow_1",
            config={"cron": "0 9 * * *"}  # 9 AM daily
        )

        trigger = ScheduleTrigger(config, on_trigger)
        await trigger.start()
        ```
    """

    def __init__(self, config: TriggerConfig, callback: Callable[[TriggerEvent], None]):
        super().__init__(config, callback)
        self.cron_expression = config.config.get("cron", "0 * * * *")  # Default: hourly
        self._task = None

    async def start(self) -> None:
        """Start the schedule trigger."""
        if self._running:
            return

        self._running = True
        self.status = TriggerStatus.ACTIVE
        self._task = asyncio.create_task(self._run())
        logger.info(f"Schedule trigger {self.config.id} started with cron: {self.cron_expression}")

    async def stop(self) -> None:
        """Stop the schedule trigger."""
        self._running = False
        if self._task:
            self._task.cancel()
        self.status = TriggerStatus.INACTIVE
        logger.info(f"Schedule trigger {self.config.id} stopped")

    async def _run(self) -> None:
        """Run the schedule loop."""
        cron = croniter(self.cron_expression, datetime.now())

        while self._running:
            next_run = cron.get_next(datetime)
            now = datetime.now()

            # Wait until next scheduled time
            wait_seconds = (next_run - now).total_seconds()
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

            if self._running and self.config.enabled:
                logger.info(f"Firing schedule trigger {self.config.id}")
                self.status = TriggerStatus.RUNNING
                self._fire({"scheduled_time": next_run.isoformat()})
                self.status = TriggerStatus.ACTIVE


class IntervalTrigger(BaseTrigger):
    """Fixed interval trigger (like n8n Interval Trigger).

    Example:
        ```python
        config = TriggerConfig(
            id="interval_1",
            name="Every 5 Minutes",
            type=TriggerType.INTERVAL,
            workflow_id="workflow_1",
            config={"interval_seconds": 300}  # 5 minutes
        )

        trigger = IntervalTrigger(config, on_trigger)
        await trigger.start()
        ```
    """

    def __init__(self, config: TriggerConfig, callback: Callable[[TriggerEvent], None]):
        super().__init__(config, callback)
        self.interval_seconds = config.config.get("interval_seconds", 60)
        self._task = None

    async def start(self) -> None:
        """Start the interval trigger."""
        if self._running:
            return

        self._running = True
        self.status = TriggerStatus.ACTIVE
        self._task = asyncio.create_task(self._run())
        logger.info(f"Interval trigger {self.config.id} started with {self.interval_seconds}s interval")

    async def stop(self) -> None:
        """Stop the interval trigger."""
        self._running = False
        if self._task:
            self._task.cancel()
        self.status = TriggerStatus.INACTIVE
        logger.info(f"Interval trigger {self.config.id} stopped")

    async def _run(self) -> None:
        """Run the interval loop."""
        while self._running:
            await asyncio.sleep(self.interval_seconds)

            if self._running and self.config.enabled:
                logger.info(f"Firing interval trigger {self.config.id}")
                self.status = TriggerStatus.RUNNING
                self._fire({"execution_time": datetime.now().isoformat()})
                self.status = TriggerStatus.ACTIVE


class WebhookTrigger(BaseTrigger):
    """Webhook trigger for HTTP endpoints (like n8n Webhook Trigger).

    Note: Requires a web server to be set up separately.
    This class manages the webhook configuration.

    Example:
        ```python
        config = TriggerConfig(
            id="webhook_1",
            name="API Webhook",
            type=TriggerType.WEBHOOK,
            workflow_id="workflow_1",
            config={
                "path": "/webhook/api",
                "method": "POST",
                "response_mode": "immediate"
            }
        )

        trigger = WebhookTrigger(config, on_trigger)
        ```
    """

    def __init__(self, config: TriggerConfig, callback: Callable[[TriggerEvent], None]):
        super().__init__(config, callback)
        self.path = config.config.get("path", "/webhook")
        self.method = config.config.get("method", "POST")
        self.response_mode = config.config.get("response_mode", "immediate")

    async def start(self) -> None:
        """Start the webhook trigger."""
        self._running = True
        self.status = TriggerStatus.ACTIVE
        logger.info(f"Webhook trigger {self.config.id} ready at {self.path}")

    async def stop(self) -> None:
        """Stop the webhook trigger."""
        self._running = False
        self.status = TriggerStatus.INACTIVE
        logger.info(f"Webhook trigger {self.config.id} stopped")

    def handle_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming webhook request.

        Args:
            data: Request data (body, headers, query params)

        Returns:
            Response data
        """
        if not self._running or not self.config.enabled:
            return {"error": "Webhook is disabled"}

        logger.info(f"Webhook {self.config.id} received request")
        self.status = TriggerStatus.RUNNING
        self._fire(data)
        self.status = TriggerStatus.ACTIVE

        return {"success": True, "message": "Webhook received"}


class ManualTrigger(BaseTrigger):
    """Manual trigger for on-demand execution.

    Example:
        ```python
        config = TriggerConfig(
            id="manual_1",
            name="Manual Execution",
            type=TriggerType.MANUAL,
            workflow_id="workflow_1"
        )

        trigger = ManualTrigger(config, on_trigger)
        trigger.execute({"user_id": "123", "reason": "test"})
        ```
    """

    async def start(self) -> None:
        """Start the manual trigger (always ready)."""
        self._running = True
        self.status = TriggerStatus.ACTIVE
        logger.info(f"Manual trigger {self.config.id} ready")

    async def stop(self) -> None:
        """Stop the manual trigger."""
        self._running = False
        self.status = TriggerStatus.INACTIVE

    def execute(self, data: dict[str, Any] = None) -> None:
        """Manually execute the trigger.

        Args:
            data: Execution data
        """
        if not self._running or not self.config.enabled:
            logger.warning(f"Manual trigger {self.config.id} is disabled")
            return

        logger.info(f"Manual trigger {self.config.id} executed")
        self.status = TriggerStatus.RUNNING
        self._fire(data or {})
        self.status = TriggerStatus.ACTIVE


class TriggerManager:
    """Manages multiple triggers for workflows.

    Example:
        ```python
        from unify_llm.agent.triggers import TriggerManager

        manager = TriggerManager()

        # Add triggers
        manager.add_trigger(schedule_trigger)
        manager.add_trigger(webhook_trigger)

        # Start all
        await manager.start_all()

        # Stop specific trigger
        await manager.stop_trigger("schedule_1")
        ```
    """

    def __init__(self):
        self.triggers: dict[str, BaseTrigger] = {}

    def add_trigger(self, trigger: BaseTrigger) -> None:
        """Add a trigger to the manager.

        Args:
            trigger: Trigger instance
        """
        self.triggers[trigger.config.id] = trigger
        logger.info(f"Added trigger {trigger.config.id}")

    def remove_trigger(self, trigger_id: str) -> None:
        """Remove a trigger.

        Args:
            trigger_id: Trigger ID
        """
        if trigger_id in self.triggers:
            del self.triggers[trigger_id]
            logger.info(f"Removed trigger {trigger_id}")

    async def start_trigger(self, trigger_id: str) -> None:
        """Start a specific trigger.

        Args:
            trigger_id: Trigger ID
        """
        if trigger_id in self.triggers:
            await self.triggers[trigger_id].start()

    async def stop_trigger(self, trigger_id: str) -> None:
        """Stop a specific trigger.

        Args:
            trigger_id: Trigger ID
        """
        if trigger_id in self.triggers:
            await self.triggers[trigger_id].stop()

    async def start_all(self) -> None:
        """Start all triggers."""
        for trigger in self.triggers.values():
            if trigger.config.enabled:
                await trigger.start()
        logger.info(f"Started {len(self.triggers)} triggers")

    async def stop_all(self) -> None:
        """Stop all triggers."""
        for trigger in self.triggers.values():
            await trigger.stop()
        logger.info("Stopped all triggers")

    def get_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all triggers.

        Returns:
            Status information for each trigger
        """
        return {
            trigger_id: {
                "name": trigger.config.name,
                "type": trigger.config.type,
                "status": trigger.status,
                "enabled": trigger.config.enabled,
                "workflow_id": trigger.config.workflow_id
            }
            for trigger_id, trigger in self.triggers.items()
        }
