"""Core data models for UnifyLLM."""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class Role(StrEnum):
    """Message sender role. StrEnum (str subclass) — 可从字符串强制、序列化为字面值。"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class FinishReason(StrEnum):
    """Why generation stopped. StrEnum — 向后兼容历史的字符串字面值。"""

    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"


class Message(BaseModel):
    """Represents a single message in a conversation.

    Attributes:
        role: The role of the message sender (system, user, assistant, tool)
        content: The content of the message
        name: Optional name of the sender
        tool_calls: Optional list of tool calls (for assistant messages)
        tool_call_id: Optional ID of the tool call (for tool response messages)
    """

    role: Role
    content: str | None = None
    name: str | None = None
    tool_calls: list[dict[str, object]] | None = None
    tool_call_id: str | None = None

    @model_validator(mode="after")
    def validate_content(self) -> "Message":
        """Validate that content is provided for most message types.

        历史语义(保持不变):仅当 ``content`` 被显式提供时才校验(等价于旧
        ``@field_validator`` 的 ``validate_default=False``);``tool`` 角色允许空 content,
        其余角色要求非空。
        """
        # content 未显式提供时不校验
        if "content" not in self.model_fields_set:
            return self

        # Tool messages might have empty content in some cases
        if self.role == Role.TOOL:
            return self

        # Other messages should have content
        if self.content is None or self.content.strip() == "":
            raise ValueError(f"Content is required for {self.role} messages")

        return self


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
    messages: list[Message]
    temperature: float | None = Field(default=1.0, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    top_p: float | None = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: float | None = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float | None = Field(default=0.0, ge=-2.0, le=2.0)
    stop: str | list[str] | None = None
    stream: bool = False
    tools: list[dict[str, object]] | None = None
    tool_choice: str | dict[str, object] | None = None
    response_format: dict[str, str] | None = None
    user: str | None = None
    extra_params: dict[str, object] = Field(default_factory=dict)

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: list[Message]) -> list[Message]:
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
    finish_reason: FinishReason | None = None


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
    choices: list[ChatResponseChoice]
    usage: Usage | None = None
    created: int
    provider: str
    raw_response: dict[str, object] | None = None

    @property
    def content(self) -> str | None:
        """Get the content of the first choice."""
        if self.choices:
            return self.choices[0].message.content
        return None

    @property
    def finish_reason(self) -> str | None:
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
    choices: list["StreamChoiceDelta"]
    created: int
    provider: str

    @property
    def content(self) -> str | None:
        """Get the content delta of the first choice."""
        if self.choices:
            return self.choices[0].delta.content
        return None

    @property
    def finish_reason(self) -> str | None:
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

    role: Role | None = None
    content: str | None = None
    tool_calls: list[dict[str, object]] | None = None


class StreamChoiceDelta(BaseModel):
    """Represents a choice delta in a streaming response.

    Attributes:
        index: The index of this choice
        delta: The message delta
        finish_reason: Why the generation stopped (only in final chunk)
    """

    index: int
    delta: MessageDelta
    finish_reason: FinishReason | None = None


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

    api_key: str | None = None
    base_url: str | None = None
    timeout: float = 60.0
    max_retries: int = 3
    organization: str | None = None
    extra_headers: dict[str, str] = Field(default_factory=dict)
