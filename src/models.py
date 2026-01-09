"""Core data models for UnifyLLM."""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


class Message(BaseModel):
    """Represents a single message in a conversation.

    Attributes:
        role: The role of the message sender (system, user, assistant, tool)
        content: The content of the message
        name: Optional name of the sender
        tool_calls: Optional list of tool calls (for assistant messages)
        tool_call_id: Optional ID of the tool call (for tool response messages)
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: Optional[str], info) -> Optional[str]:
        """Validate that content is provided for most message types."""
        role = info.data.get("role")
        tool_calls = info.data.get("tool_calls")

        # Assistant messages with tool_calls can have empty content
        if role == "assistant" and tool_calls:
            return v

        # Tool messages might have empty content in some cases
        if role == "tool":
            return v

        # Other messages should have content
        if v is None or v.strip() == "":
            raise ValueError(f"Content is required for {role} messages")

        return v


class Usage(BaseModel):
    """Token usage information.

    Attributes:
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total number of tokens used
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatRequest(BaseModel):
    """Represents a chat completion request.

    Attributes:
        model: The model identifier (e.g., "gpt-4", "claude-3-opus")
        messages: List of conversation messages
        temperature: Sampling temperature (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        top_p: Nucleus sampling parameter
        frequency_penalty: Frequency penalty (-2.0 to 2.0)
        presence_penalty: Presence penalty (-2.0 to 2.0)
        stop: Stop sequences
        stream: Whether to stream the response
        tools: Available tools for function calling
        tool_choice: How to select tools
        response_format: Desired response format
        user: Unique identifier for the end-user
        extra_params: Provider-specific extra parameters
    """

    model: str
    messages: List[Message]
    temperature: Optional[float] = Field(default=1.0, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    stop: Optional[Union[str, List[str]]] = None
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, str]] = None
    user: Optional[str] = None
    extra_params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: List[Message]) -> List[Message]:
        """Validate that messages list is not empty."""
        if not v:
            raise ValueError("Messages list cannot be empty")
        return v


class ChatResponseChoice(BaseModel):
    """Represents a single choice in a chat response.

    Attributes:
        index: The index of this choice
        message: The generated message
        finish_reason: Why the generation stopped
    """

    index: int
    message: Message
    finish_reason: Optional[Literal["stop", "length", "tool_calls", "content_filter"]] = None


class ChatResponse(BaseModel):
    """Represents a chat completion response.

    Attributes:
        id: Unique identifier for the response
        model: The model that generated the response
        choices: List of generated choices
        usage: Token usage information
        created: Unix timestamp of creation
        provider: The provider that generated the response
        raw_response: The raw response from the provider (optional)
    """

    id: str
    model: str
    choices: List[ChatResponseChoice]
    usage: Optional[Usage] = None
    created: int
    provider: str
    raw_response: Optional[Dict[str, Any]] = None

    @property
    def content(self) -> Optional[str]:
        """Get the content of the first choice."""
        if self.choices:
            return self.choices[0].message.content
        return None

    @property
    def finish_reason(self) -> Optional[str]:
        """Get the finish reason of the first choice."""
        if self.choices:
            return self.choices[0].finish_reason
        return None


class StreamChunk(BaseModel):
    """Represents a chunk in a streaming response.

    Attributes:
        id: Unique identifier for the stream
        model: The model generating the stream
        choices: List of choice deltas
        created: Unix timestamp of creation
        provider: The provider generating the stream
    """

    id: str
    model: str
    choices: List["StreamChoiceDelta"]
    created: int
    provider: str

    @property
    def content(self) -> Optional[str]:
        """Get the content delta of the first choice."""
        if self.choices:
            return self.choices[0].delta.content
        return None

    @property
    def finish_reason(self) -> Optional[str]:
        """Get the finish reason of the first choice."""
        if self.choices:
            return self.choices[0].finish_reason
        return None


class MessageDelta(BaseModel):
    """Represents a delta (incremental update) to a message.

    Attributes:
        role: The role of the message (only in first chunk)
        content: The content delta
        tool_calls: Tool calls delta
    """

    role: Optional[Literal["system", "user", "assistant", "tool"]] = None
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class StreamChoiceDelta(BaseModel):
    """Represents a choice delta in a streaming response.

    Attributes:
        index: The index of this choice
        delta: The message delta
        finish_reason: Why the generation stopped (only in final chunk)
    """

    index: int
    delta: MessageDelta
    finish_reason: Optional[Literal["stop", "length", "tool_calls", "content_filter"]] = None


class ProviderConfig(BaseModel):
    """Configuration for a provider.

    Attributes:
        api_key: API key for authentication
        base_url: Base URL for the API (optional, for custom endpoints)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        organization: Organization ID (for providers that support it)
        extra_headers: Additional headers to include in requests
    """

    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: float = 60.0
    max_retries: int = 3
    organization: Optional[str] = None
    extra_headers: Dict[str, str] = Field(default_factory=dict)
