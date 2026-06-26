"""Unified client for LLM providers(兼容门面:内部委托 ports.factory 的唯一注册表/装配缝)。"""

from collections.abc import AsyncIterator, Iterator
from typing import ClassVar

from unify_llm.adapters.base import BaseProvider
from unify_llm.core.exceptions import InvalidRequestError
from unify_llm.models import (
    ChatRequest,
    ChatResponse,
    Message,
    ProviderConfig,
    StreamChunk,
)
from unify_llm.ports import factory
from unify_llm.ports.factory import ProviderBuilder
from unify_llm.ports.llm import LLMProvider
from unify_llm.utils import get_api_key_from_env, resolve_model_name


class UnifyLLM:
    """Unified client for calling various LLM APIs.

    This is the main entry point for using UnifyLLM. It provides a simple,
    consistent interface for calling different LLM providers.

    Example:
        ```python
        from unify_llm import UnifyLLM

        # Initialize with OpenAI
        client = UnifyLLM(provider="openai", api_key="sk-...")

        # Make a simple chat request
        response = client.chat(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        print(response.content)

        # Stream a response
        for chunk in client.chat_stream(
            model="gpt-4",
            messages=[{"role": "user", "content": "Tell me a story"}]
        ):
            print(chunk.content, end="")
        ```
    """

    # 唯一 provider 表收编进 ports.factory;此处保留同一引用以兼容历史的成员判断/注册。
    _providers: ClassVar[dict[str, ProviderBuilder]] = factory.REGISTRY

    def __init__(
        self,
        provider: str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        organization: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize the UnifyLLM client.

        Args:
            provider: The provider name (e.g., "openai", "anthropic")
            api_key: API key for authentication. If not provided, will attempt
                     to read from environment variable (e.g., OPENAI_API_KEY).
            base_url: Custom base URL (optional)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            organization: Organization ID (for providers that support it)
            extra_headers: Additional headers to include in requests

        Raises:
            InvalidRequestError: If the provider is not supported
        """
        # Auto-load API key from environment if not provided
        if api_key is None:
            api_key = get_api_key_from_env(provider)

        # Create provider config
        config = ProviderConfig(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            organization=organization,
            extra_headers=extra_headers or {},
        )

        # 委托唯一装配缝纯查表构造(未知 provider → InvalidRequestError)。
        # 门面语义:显式选定即如实构造,不做 Mock 回退(缺 key 留到调用时报错)。
        self._provider: LLMProvider = factory.build(provider, config)
        self._provider_name = provider  # Save for model name resolution

    @classmethod
    def register_provider(cls, name: str, provider_class: type[BaseProvider]) -> None:
        """Register a custom provider.

        This allows users to add their own provider implementations.

        Args:
            name: Name of the provider
            provider_class: Provider class (must inherit from BaseProvider)

        Example:
            ```python
            from unify_llm import UnifyLLM
            from unify_llm.providers import BaseProvider

            class MyProvider(BaseProvider):
                # ... implementation ...

            UnifyLLM.register_provider("myprovider", MyProvider)
            client = UnifyLLM(provider="myprovider", api_key="...")
            ```
        """
        if not issubclass(provider_class, BaseProvider):
            raise InvalidRequestError("Provider class must inherit from BaseProvider")
        factory.register(name, provider_class)

    def _prepare_chat_request(
        self,
        model: str,
        messages: list[Message | dict[str, str]],
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        frequency_penalty: float | None = None,
        presence_penalty: float | None = None,
        stop: str | list[str] | None = None,
        tools: list[dict[str, object]] | None = None,
        tool_choice: str | dict[str, object] | None = None,
        response_format: dict[str, str] | None = None,
        user: str | None = None,
        extra_params: dict[str, object] | None = None,
    ) -> ChatRequest:
        """Prepare a chat request (shared logic for sync/async methods).

        Args:
            model: Model identifier
            messages: List of messages
            stream: Whether to stream the response
            extra_params: Additional provider-specific parameters

        Returns:
            Prepared ChatRequest object
        """
        # Resolve model alias to full name
        resolved_model = resolve_model_name(self._provider_name, model)

        # Convert dict messages to Message objects
        parsed_messages = [
            msg if isinstance(msg, Message) else Message.model_validate(msg) for msg in messages
        ]

        return ChatRequest(
            model=resolved_model,
            messages=parsed_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            stream=stream,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
            user=user,
            extra_params=extra_params or {},
        )

    def chat(
        self,
        model: str,
        messages: list[Message | dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        frequency_penalty: float | None = None,
        presence_penalty: float | None = None,
        stop: str | list[str] | None = None,
        tools: list[dict[str, object]] | None = None,
        tool_choice: str | dict[str, object] | None = None,
        response_format: dict[str, str] | None = None,
        user: str | None = None,
        **extra_params: object,
    ) -> ChatResponse:
        """Make a synchronous chat request.

        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3-opus")
            messages: List of messages (can be Message objects or dicts)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Frequency penalty (-2.0 to 2.0)
            presence_penalty: Presence penalty (-2.0 to 2.0)
            stop: Stop sequences
            tools: Available tools for function calling
            tool_choice: How to select tools
            response_format: Desired response format
            user: Unique identifier for the end-user
            **extra_params: Provider-specific extra parameters

        Returns:
            Chat response

        Example:
            ```python
            response = client.chat(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What is Python?"}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            print(response.content)
            ```
        """
        request = self._prepare_chat_request(
            model=model,
            messages=messages,
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
            user=user,
            extra_params=extra_params,
        )
        return self._provider.chat(request)

    async def achat(
        self,
        model: str,
        messages: list[Message | dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        frequency_penalty: float | None = None,
        presence_penalty: float | None = None,
        stop: str | list[str] | None = None,
        tools: list[dict[str, object]] | None = None,
        tool_choice: str | dict[str, object] | None = None,
        response_format: dict[str, str] | None = None,
        user: str | None = None,
        **extra_params: object,
    ) -> ChatResponse:
        """Make an asynchronous chat request.

        Same as chat() but runs asynchronously.

        Example:
            ```python
            response = await client.achat(
                model="gpt-4",
                messages=[{"role": "user", "content": "Hello!"}]
            )
            ```
        """
        request = self._prepare_chat_request(
            model=model,
            messages=messages,
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
            user=user,
            extra_params=extra_params,
        )
        return await self._provider.achat(request)

    def chat_stream(
        self,
        model: str,
        messages: list[Message | dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        frequency_penalty: float | None = None,
        presence_penalty: float | None = None,
        stop: str | list[str] | None = None,
        tools: list[dict[str, object]] | None = None,
        tool_choice: str | dict[str, object] | None = None,
        user: str | None = None,
        **extra_params: object,
    ) -> Iterator[StreamChunk]:
        """Make a synchronous streaming chat request.

        Args:
            Same as chat(), but returns an iterator of chunks

        Yields:
            Stream chunks

        Example:
            ```python
            for chunk in client.chat_stream(
                model="gpt-4",
                messages=[{"role": "user", "content": "Tell me a story"}]
            ):
                if chunk.content:
                    print(chunk.content, end="", flush=True)
            ```
        """
        request = self._prepare_chat_request(
            model=model,
            messages=messages,
            stream=True,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            tools=tools,
            tool_choice=tool_choice,
            user=user,
            extra_params=extra_params,
        )
        yield from self._provider.chat_stream(request)

    async def achat_stream(
        self,
        model: str,
        messages: list[Message | dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        frequency_penalty: float | None = None,
        presence_penalty: float | None = None,
        stop: str | list[str] | None = None,
        tools: list[dict[str, object]] | None = None,
        tool_choice: str | dict[str, object] | None = None,
        user: str | None = None,
        **extra_params: object,
    ) -> AsyncIterator[StreamChunk]:
        """Make an asynchronous streaming chat request.

        Same as chat_stream() but runs asynchronously.

        Example:
            ```python
            async for chunk in client.achat_stream(
                model="gpt-4",
                messages=[{"role": "user", "content": "Tell me a story"}]
            ):
                if chunk.content:
                    print(chunk.content, end="", flush=True)
            ```
        """
        request = self._prepare_chat_request(
            model=model,
            messages=messages,
            stream=True,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            tools=tools,
            tool_choice=tool_choice,
            user=user,
            extra_params=extra_params,
        )
        async for chunk in self._provider.achat_stream(request):
            yield chunk
