"""Unified client for LLM providers."""

from typing import AsyncIterator, Dict, Iterator, List, Optional, Type, Union

from unify_llm.models import (
    ChatRequest,
    ChatResponse,
    Message,
    ProviderConfig,
    StreamChunk,
)
from unify_llm.providers.base import BaseProvider
from unify_llm.providers.openai import OpenAIProvider
from unify_llm.providers.anthropic import AnthropicProvider
from unify_llm.providers.gemini import GeminiProvider
from unify_llm.providers.ollama import OllamaProvider
from unify_llm.exceptions import InvalidRequestError


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

    # Registry of available providers
    _providers: Dict[str, Type[BaseProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
        "ollama": OllamaProvider,
    }

    def __init__(
        self,
        provider: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        organization: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ):
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
        if provider not in self._providers:
            available = ", ".join(self._providers.keys())
            raise InvalidRequestError(
                f"Provider '{provider}' not supported. Available providers: {available}"
            )

        # Auto-load API key from environment if not provided
        if api_key is None:
            from unify_llm.utils import get_api_key_from_env
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

        # Initialize provider
        provider_class = self._providers[provider]
        self._provider: BaseProvider = provider_class(config)

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseProvider]) -> None:
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
            raise InvalidRequestError(
                f"Provider class must inherit from BaseProvider"
            )
        cls._providers[name] = provider_class

    def chat(
        self,
        model: str,
        messages: List[Union[Message, Dict[str, str]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
        response_format: Optional[Dict[str, str]] = None,
        user: Optional[str] = None,
        **extra_params,
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
        # Convert dict messages to Message objects
        parsed_messages = [
            msg if isinstance(msg, Message) else Message(**msg)
            for msg in messages
        ]

        request = ChatRequest(
            model=model,
            messages=parsed_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            stream=False,
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
        messages: List[Union[Message, Dict[str, str]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
        response_format: Optional[Dict[str, str]] = None,
        user: Optional[str] = None,
        **extra_params,
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
        # Convert dict messages to Message objects
        parsed_messages = [
            msg if isinstance(msg, Message) else Message(**msg)
            for msg in messages
        ]

        request = ChatRequest(
            model=model,
            messages=parsed_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            stream=False,
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
        messages: List[Union[Message, Dict[str, str]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
        user: Optional[str] = None,
        **extra_params,
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
        # Convert dict messages to Message objects
        parsed_messages = [
            msg if isinstance(msg, Message) else Message(**msg)
            for msg in messages
        ]

        request = ChatRequest(
            model=model,
            messages=parsed_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            stream=True,
            tools=tools,
            tool_choice=tool_choice,
            user=user,
            extra_params=extra_params,
        )

        yield from self._provider.chat_stream(request)

    async def achat_stream(
        self,
        model: str,
        messages: List[Union[Message, Dict[str, str]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
        user: Optional[str] = None,
        **extra_params,
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
        # Convert dict messages to Message objects
        parsed_messages = [
            msg if isinstance(msg, Message) else Message(**msg)
            for msg in messages
        ]

        request = ChatRequest(
            model=model,
            messages=parsed_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            stream=True,
            tools=tools,
            tool_choice=tool_choice,
            user=user,
            extra_params=extra_params,
        )

        async for chunk in self._provider.achat_stream(request):
            yield chunk
