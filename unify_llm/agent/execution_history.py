"""Execution history and persistence for workflows (n8n-style).

This module provides execution history tracking and persistence,
similar to n8n's execution data storage.
"""


from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Execution status."""
    SUCCESS = "success"
    RUNNING = "running"
    ERROR = "error"
    WAITING = "waiting"
    CANCELED = "canceled"


class ExecutionData(BaseModel):
    """Data for a single execution.

    Attributes:
        id: Unique execution ID
        workflow_id: Associated workflow ID
        workflow_name: Workflow name
        status: Execution status
        start_time: When execution started
        end_time: When execution ended
        trigger_type: Type of trigger that started execution
        input_data: Input data
        output_data: Output data
        error: Error message if failed
        node_executions: Per-node execution data
        metadata: Additional metadata
    """

    id: str = Field(..., description="Execution ID")
    workflow_id: str = Field(..., description="Workflow ID")
    workflow_name: str = Field(..., description="Workflow name")
    status: ExecutionStatus = Field(..., description="Execution status")
    start_time: datetime = Field(..., description="Start time")
    end_time: datetime | None = Field(default=None, description="End time")
    trigger_type: str | None = Field(default=None, description="Trigger type")
    input_data: dict[str, Any] = Field(default_factory=dict, description="Input data")
    output_data: dict[str, Any] | None = Field(default=None, description="Output data")
    error: str | None = Field(default=None, description="Error message")
    node_executions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Node execution data"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")

    @property
    def duration(self) -> float | None:
        """Get execution duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class ExecutionHistory:
    """Manages execution history with SQLite persistence (n8n-style).

    Example:
        ```python
        from unify_llm.agent.execution_history import ExecutionHistory, ExecutionData, ExecutionStatus

        # Initialize history
        history = ExecutionHistory(db_path="executions.db")

        # Save execution
        execution = ExecutionData(
            id="exec_123",
            workflow_id="workflow_1",
            workflow_name="Daily Report",
            status=ExecutionStatus.SUCCESS,
            start_time=datetime.now(),
            input_data={"date": "2024-01-01"}
        )
        history.save(execution)

        # Query executions
        recent = history.get_recent(limit=10)
        by_workflow = history.get_by_workflow("workflow_1", limit=20)
        ```
    """

    def __init__(self, db_path: str = "execution_history.db"):
        """Initialize execution history.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                workflow_name TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                trigger_type TEXT,
                input_data TEXT,
                output_data TEXT,
                error TEXT,
                node_executions TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_id
            ON executions(workflow_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status
            ON executions(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_start_time
            ON executions(start_time DESC)
        """)

        conn.commit()
        conn.close()

        logger.info(f"Initialized execution history database: {self.db_path}")

    def save(self, execution: ExecutionData) -> None:
        """Save an execution to history.

        Args:
            execution: Execution data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO executions
            (id, workflow_id, workflow_name, status, start_time, end_time,
             trigger_type, input_data, output_data, error, node_executions, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution.id,
            execution.workflow_id,
            execution.workflow_name,
            execution.status,
            execution.start_time.isoformat(),
            execution.end_time.isoformat() if execution.end_time else None,
            execution.trigger_type,
            json.dumps(execution.input_data),
            json.dumps(execution.output_data) if execution.output_data else None,
            execution.error,
            json.dumps(execution.node_executions),
            json.dumps(execution.metadata)
        ))

        conn.commit()
        conn.close()

        logger.debug(f"Saved execution {execution.id}")

    def get(self, execution_id: str) -> ExecutionData | None:
        """Get execution by ID.

        Args:
            execution_id: Execution ID

        Returns:
            Execution data or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, workflow_id, workflow_name, status, start_time, end_time,
                   trigger_type, input_data, output_data, error, node_executions, metadata
            FROM executions
            WHERE id = ?
        """, (execution_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_execution(row)

    def get_recent(self, limit: int = 50, status: str | None = None) -> list[ExecutionData]:
        """Get recent executions.

        Args:
            limit: Maximum number of executions
            status: Filter by status

        Returns:
            List of executions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if status:
            cursor.execute("""
                SELECT id, workflow_id, workflow_name, status, start_time, end_time,
                       trigger_type, input_data, output_data, error, node_executions, metadata
                FROM executions
                WHERE status = ?
                ORDER BY start_time DESC
                LIMIT ?
            """, (status, limit))
        else:
            cursor.execute("""
                SELECT id, workflow_id, workflow_name, status, start_time, end_time,
                       trigger_type, input_data, output_data, error, node_executions, metadata
                FROM executions
                ORDER BY start_time DESC
                LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_execution(row) for row in rows]

    def get_by_workflow(
        self,
        workflow_id: str,
        limit: int = 50,
        status: str | None = None
    ) -> list[ExecutionData]:
        """Get executions for a specific workflow.

        Args:
            workflow_id: Workflow ID
            limit: Maximum number of executions
            status: Filter by status

        Returns:
            List of executions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if status:
            cursor.execute("""
                SELECT id, workflow_id, workflow_name, status, start_time, end_time,
                       trigger_type, input_data, output_data, error, node_executions, metadata
                FROM executions
                WHERE workflow_id = ? AND status = ?
                ORDER BY start_time DESC
                LIMIT ?
            """, (workflow_id, status, limit))
        else:
            cursor.execute("""
                SELECT id, workflow_id, workflow_name, status, start_time, end_time,
                       trigger_type, input_data, output_data, error, node_executions, metadata
                FROM executions
                WHERE workflow_id = ?
                ORDER BY start_time DESC
                LIMIT ?
            """, (workflow_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_execution(row) for row in rows]

    def get_statistics(self, workflow_id: str | None = None) -> dict[str, Any]:
        """Get execution statistics.

        Args:
            workflow_id: Optional workflow ID to filter

        Returns:
            Statistics data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if workflow_id:
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running
                FROM executions
                WHERE workflow_id = ?
            """, (workflow_id,))
        else:
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running
                FROM executions
            """)

        row = cursor.fetchone()
        conn.close()

        total, success, error, running = row
        success_rate = (success / total * 100) if total > 0 else 0

        return {
            "total": total,
            "success": success,
            "error": error,
            "running": running,
            "success_rate": round(success_rate, 2)
        }

    def delete_old(self, days: int = 30) -> int:
        """Delete executions older than specified days.

        Args:
            days: Number of days

        Returns:
            Number of deleted executions
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM executions
            WHERE start_time < ?
        """, (cutoff_date.isoformat(),))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Deleted {deleted} executions older than {days} days")
        return deleted

    def _row_to_execution(self, row: tuple) -> ExecutionData:
        """Convert database row to ExecutionData.

        Args:
            row: Database row

        Returns:
            ExecutionData instance
        """
        return ExecutionData(
            id=row[0],
            workflow_id=row[1],
            workflow_name=row[2],
            status=row[3],
            start_time=datetime.fromisoformat(row[4]),
            end_time=datetime.fromisoformat(row[5]) if row[5] else None,
            trigger_type=row[6],
            input_data=json.loads(row[7]) if row[7] else {},
            output_data=json.loads(row[8]) if row[8] else None,
            error=row[9],
            node_executions=json.loads(row[10]) if row[10] else [],
            metadata=json.loads(row[11]) if row[11] else {}
        )
