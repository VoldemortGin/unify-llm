"""Memory management for AI agents."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryMessageRole(str, Enum):
    """Roles for memory messages."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MemoryMessage(BaseModel):
    """A message in conversation memory.

    Attributes:
        role: Message role (system, user, assistant, tool)
        content: Message content
        name: Optional name (for tool messages)
        tool_call_id: Optional tool call ID
        timestamp: When the message was created
        metadata: Additional metadata
    """

    role: MemoryMessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    name: Optional[str] = Field(default=None, description="Message name")
    tool_call_id: Optional[str] = Field(default=None, description="Tool call ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for LLM.

        Returns:
            Message as dict
        """
        msg = {"role": self.role, "content": self.content}
        if self.name:
            msg["name"] = self.name
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        return msg


class ConversationMemory:
    """Manages conversation history for an agent.

    Implements a sliding window memory that keeps the most recent N messages.

    Example:
        ```python
        from src.agent import ConversationMemory

        # Create memory with window of 10 messages
        memory = ConversationMemory(window_size=10)

        # Add messages
        memory.add_user_message("Hello!")
        memory.add_assistant_message("Hi! How can I help you?")
        memory.add_user_message("What's the weather?")

        # Get messages for LLM
        messages = memory.get_messages()

        # Clear memory
        memory.clear()
        ```
    """

    def __init__(self, window_size: int = 10):
        """Initialize conversation memory.

        Args:
            window_size: Number of messages to keep in memory
        """
        self.window_size = window_size
        self._messages: List[MemoryMessage] = []

    def add_message(self, message: MemoryMessage) -> None:
        """Add a message to memory.

        Args:
            message: Message to add
        """
        self._messages.append(message)
        self._trim_to_window()

    def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a user message.

        Args:
            content: Message content
            metadata: Optional metadata
        """
        message = MemoryMessage(
            role=MemoryMessageRole.USER,
            content=content,
            metadata=metadata or {}
        )
        self.add_message(message)

    def add_assistant_message(
            self,
            content: str,
            metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an assistant message.

        Args:
            content: Message content
            metadata: Optional metadata
        """
        message = MemoryMessage(
            role=MemoryMessageRole.ASSISTANT,
            content=content,
            metadata=metadata or {}
        )
        self.add_message(message)

    def add_system_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a system message.

        Args:
            content: Message content
            metadata: Optional metadata
        """
        message = MemoryMessage(
            role=MemoryMessageRole.SYSTEM,
            content=content,
            metadata=metadata or {}
        )
        self.add_message(message)

    def add_tool_message(
            self,
            content: str,
            name: str,
            tool_call_id: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a tool result message.

        Args:
            content: Tool result content
            name: Tool name
            tool_call_id: Tool call ID
            metadata: Optional metadata
        """
        message = MemoryMessage(
            role=MemoryMessageRole.TOOL,
            content=content,
            name=name,
            tool_call_id=tool_call_id,
            metadata=metadata or {}
        )
        self.add_message(message)

    def get_messages(self, include_system: bool = True) -> List[Dict[str, Any]]:
        """Get messages in LLM format.

        Args:
            include_system: Whether to include system messages

        Returns:
            List of message dicts
        """
        messages = []
        for msg in self._messages:
            if not include_system and msg.role == MemoryMessageRole.SYSTEM:
                continue
            messages.append(msg.to_dict())
        return messages

    def get_recent_messages(self, n: int) -> List[MemoryMessage]:
        """Get the N most recent messages.

        Args:
            n: Number of messages to retrieve

        Returns:
            List of recent messages
        """
        return self._messages[-n:] if n < len(self._messages) else self._messages

    def clear(self) -> None:
        """Clear all messages from memory."""
        self._messages.clear()

    def _trim_to_window(self) -> None:
        """Trim messages to fit within the window size."""
        if len(self._messages) > self.window_size:
            # Keep system messages and trim user/assistant messages
            system_messages = [m for m in self._messages if m.role == MemoryMessageRole.SYSTEM]
            other_messages = [m for m in self._messages if m.role != MemoryMessageRole.SYSTEM]

            # Keep the most recent messages
            if len(other_messages) > (self.window_size - len(system_messages)):
                other_messages = other_messages[-(self.window_size - len(system_messages)):]

            self._messages = system_messages + other_messages

    def __len__(self) -> int:
        """Get number of messages in memory."""
        return len(self._messages)

    def __repr__(self) -> str:
        """String representation."""
        return f"ConversationMemory(window_size={self.window_size}, messages={len(self._messages)})"


class SharedMemory:
    """Shared memory for multi-agent workflows.

    Allows multiple agents to share context and information.

    Example:
        ```python
        from src.agent import SharedMemory

        # Create shared memory
        shared = SharedMemory()

        # Store data
        shared.set("user_preference", "dark_mode")
        shared.set("session_id", "abc123")

        # Retrieve data
        preference = shared.get("user_preference")

        # Check if key exists
        if shared.has("session_id"):
            print("Session active")

        # Clear all data
        shared.clear()
        ```
    """

    def __init__(self):
        """Initialize shared memory."""
        self._data: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def set(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store a value in shared memory.

        Args:
            key: Key to store under
            value: Value to store
            metadata: Optional metadata
        """
        self._data[key] = value
        if metadata:
            self._metadata[key] = metadata

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from shared memory.

        Args:
            key: Key to retrieve
            default: Default value if key not found

        Returns:
            Stored value or default
        """
        return self._data.get(key, default)

    def has(self, key: str) -> bool:
        """Check if a key exists in shared memory.

        Args:
            key: Key to check

        Returns:
            True if key exists
        """
        return key in self._data

    def delete(self, key: str) -> bool:
        """Delete a key from shared memory.

        Args:
            key: Key to delete

        Returns:
            True if deleted, False if not found
        """
        if key in self._data:
            del self._data[key]
            if key in self._metadata:
                del self._metadata[key]
            return True
        return False

    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a key.

        Args:
            key: Key to get metadata for

        Returns:
            Metadata dict or None
        """
        return self._metadata.get(key)

    def keys(self) -> List[str]:
        """Get all keys in shared memory.

        Returns:
            List of keys
        """
        return list(self._data.keys())

    def clear(self) -> None:
        """Clear all data from shared memory."""
        self._data.clear()
        self._metadata.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Export all data as a dictionary.

        Returns:
            All stored data
        """
        return self._data.copy()

    def __repr__(self) -> str:
        """String representation."""
        return f"SharedMemory(keys={len(self._data)})"
