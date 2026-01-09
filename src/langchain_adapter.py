"""LangChain-compatible adapter for UnifyLLM.

This module provides a wrapper that makes UnifyLLM compatible with LangChain's
BaseChatModel interface, allowing seamless integration with LangChain workflows.
"""

from typing import AsyncIterator, Iterator, List, Optional, Union

from src.client import UnifyLLM
from src.models import Message


class LangChainAdapter:
    """LangChain-compatible adapter for UnifyLLM.

    This adapter provides .invoke(), .stream(), .ainvoke(), and .astream() methods
    that match LangChain's interface while using UnifyLLM internally.

    Example:
        ```python
        from src import LangChainAdapter

        # Initialize with a provider
        llm = LangChainAdapter(provider="openai", api_key="sk-...")

        # Use LangChain-style invoke
        response = llm.invoke(
            messages=[{"role": "user", "content": "Hello!"}],
            model="gpt-4"
        )
        print(response)

        # Use streaming
        for chunk in llm.stream(
            messages=[{"role": "user", "content": "Tell me a story"}],
            model="gpt-4"
        ):
            print(chunk, end="", flush=True)
        ```
    """

    def __init__(
        self,
        provider: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        organization: Optional[str] = None,
        extra_headers: Optional[dict] = None,
    ):
        """Initialize the LangChain adapter.

        Args:
            provider: The provider name (e.g., "openai", "anthropic", "gemini", "ollama", "qwen", "bytedance")
            api_key: API key for authentication
            base_url: Custom base URL (optional)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            organization: Organization ID (for providers that support it)
            extra_headers: Additional headers to include in requests
        """
        self.client = UnifyLLM(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            organization=organization,
            extra_headers=extra_headers,
        )
        self._default_model: Optional[str] = None

    def invoke(
        self,
        messages: List[Union[Message, dict]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs,
    ) -> str:
        """Invoke the LLM (synchronous, non-streaming).

        This method matches LangChain's .invoke() interface.

        Args:
            messages: List of messages (LangChain format)
            model: Model identifier (required unless default_model is set)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            stop: Stop sequences
            **kwargs: Additional provider-specific parameters

        Returns:
            String response content

        Example:
            ```python
            response = llm.invoke(
                messages=[
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "What is Python?"}
                ],
                model="gpt-4",
                temperature=0.7
            )
            print(response)
            ```
        """
        if model is None and self._default_model is None:
            raise ValueError("model must be specified or default_model must be set")

        model = model or self._default_model

        response = self.client.chat(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=stop,
            **kwargs,
        )

        return response.content or ""

    async def ainvoke(
        self,
        messages: List[Union[Message, dict]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs,
    ) -> str:
        """Invoke the LLM asynchronously (non-streaming).

        This method matches LangChain's .ainvoke() interface.

        Args:
            Same as invoke()

        Returns:
            String response content

        Example:
            ```python
            response = await llm.ainvoke(
                messages=[{"role": "user", "content": "Hello!"}],
                model="gpt-4"
            )
            print(response)
            ```
        """
        if model is None and self._default_model is None:
            raise ValueError("model must be specified or default_model must be set")

        model = model or self._default_model

        response = await self.client.achat(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=stop,
            **kwargs,
        )

        return response.content or ""

    def stream(
        self,
        messages: List[Union[Message, dict]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs,
    ) -> Iterator[str]:
        """Stream the LLM response (synchronous).

        This method matches LangChain's .stream() interface.

        Args:
            Same as invoke()

        Yields:
            String chunks of content

        Example:
            ```python
            for chunk in llm.stream(
                messages=[{"role": "user", "content": "Tell me a story"}],
                model="gpt-4"
            ):
                print(chunk, end="", flush=True)
            ```
        """
        if model is None and self._default_model is None:
            raise ValueError("model must be specified or default_model must be set")

        model = model or self._default_model

        for chunk in self.client.chat_stream(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=stop,
            **kwargs,
        ):
            if chunk.content:
                yield chunk.content

    async def astream(
        self,
        messages: List[Union[Message, dict]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream the LLM response asynchronously.

        This method matches LangChain's .astream() interface.

        Args:
            Same as invoke()

        Yields:
            String chunks of content

        Example:
            ```python
            async for chunk in llm.astream(
                messages=[{"role": "user", "content": "Tell me a story"}],
                model="gpt-4"
            ):
                print(chunk, end="", flush=True)
            ```
        """
        if model is None and self._default_model is None:
            raise ValueError("model must be specified or default_model must be set")

        model = model or self._default_model

        async for chunk in self.client.achat_stream(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=stop,
            **kwargs,
        ):
            if chunk.content:
                yield chunk.content

    def set_default_model(self, model: str) -> None:
        """Set a default model for all calls.

        Args:
            model: Model identifier to use as default

        Example:
            ```python
            llm = LangChainAdapter(provider="openai", api_key="sk-...")
            llm.set_default_model("gpt-4")

            # Now you can omit the model parameter
            response = llm.invoke(messages=[{"role": "user", "content": "Hi"}])
            ```
        """
        self._default_model = model

    def get_raw_client(self) -> UnifyLLM:
        """Get the underlying UnifyLLM client.

        This allows access to the raw client for advanced use cases.

        Returns:
            The UnifyLLM client instance

        Example:
            ```python
            llm = LangChainAdapter(provider="openai")
            raw_client = llm.get_raw_client()

            # Use the raw client directly
            response = raw_client.chat(
                model="gpt-4",
                messages=[{"role": "user", "content": "Hello"}]
            )
            # Returns ChatResponse object with full metadata
            ```
        """
        return self.client
