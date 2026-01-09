"""Base provider abstract class."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Iterator, Optional

import httpx
import rootutils

ROOT_DIR = rootutils.setup_root(search_from=__file__, indicator=[".project-root"], pythonpath=True)

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.exceptions import (
    APIError,
    RateLimitError,
    TimeoutError,
)
from src.models import (
    ChatRequest,
    ChatResponse,
    ProviderConfig,
    StreamChunk,
)


class BaseProvider(ABC):
    """Abstract base class for all LLM providers.

    All provider implementations must inherit from this class and implement
    the required abstract methods.

    Attributes:
        name: The name of the provider
        config: Provider configuration
        client: HTTP client for making requests
        async_client: Async HTTP client for making requests
    """

    def __init__(self, config: ProviderConfig):
        """Initialize the provider.

        Args:
            config: Provider configuration
        """
        self.config = config
        self.name = self.__class__.__name__.replace("Provider", "").lower()

        # Create HTTP clients
        timeout = httpx.Timeout(self.config.timeout)
        headers = self._get_headers()

        self.client = httpx.Client(
            timeout=timeout,
            headers=headers,
        )

        self.async_client = httpx.AsyncClient(
            timeout=timeout,
            headers=headers,
        )

    def __del__(self):
        """Clean up HTTP clients."""
        try:
            self.client.close()
        except Exception:
            pass

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.async_client.aclose()

    @abstractmethod
    def _get_headers(self) -> dict:
        """Get headers for API requests.

        Returns:
            Dictionary of headers
        """
        pass

    @abstractmethod
    def _get_base_url(self) -> str:
        """Get the base URL for API requests.

        Returns:
            Base URL string
        """
        pass

    @abstractmethod
    def _convert_request(self, request: ChatRequest) -> dict:
        """Convert a ChatRequest to provider-specific format.

        Args:
            request: Unified chat request

        Returns:
            Provider-specific request dictionary
        """
        pass

    @abstractmethod
    def _convert_response(self, response: dict) -> ChatResponse:
        """Convert provider-specific response to ChatResponse.

        Args:
            response: Provider-specific response dictionary

        Returns:
            Unified chat response
        """
        pass

    @abstractmethod
    def _convert_stream_chunk(self, chunk: dict) -> Optional[StreamChunk]:
        """Convert provider-specific stream chunk to StreamChunk.

        Args:
            chunk: Provider-specific chunk dictionary

        Returns:
            Unified stream chunk, or None if chunk should be skipped
        """
        pass

    def _create_retry_decorator(self):
        """Create a retry decorator for API requests.

        Returns:
            Tenacity retry decorator
        """
        return retry(
            stop=stop_after_attempt(self.config.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((RateLimitError, TimeoutError, APIError)),
            reraise=True,
        )

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Make a synchronous chat request.

        Args:
            request: Chat request

        Returns:
            Chat response

        Raises:
            UnifyLLMError: If the request fails
        """
        if request.stream:
            raise ValueError("Use chat_stream() for streaming requests")

        retry_decorator = self._create_retry_decorator()
        return retry_decorator(self._chat_impl)(request)

    @abstractmethod
    def _chat_impl(self, request: ChatRequest) -> ChatResponse:
        """Implementation of synchronous chat request.

        Args:
            request: Chat request

        Returns:
            Chat response
        """
        pass

    async def achat(self, request: ChatRequest) -> ChatResponse:
        """Make an asynchronous chat request.

        Args:
            request: Chat request

        Returns:
            Chat response

        Raises:
            UnifyLLMError: If the request fails
        """
        if request.stream:
            raise ValueError("Use achat_stream() for streaming requests")

        retry_decorator = self._create_retry_decorator()
        return await retry_decorator(self._achat_impl)(request)

    @abstractmethod
    async def _achat_impl(self, request: ChatRequest) -> ChatResponse:
        """Implementation of asynchronous chat request.

        Args:
            request: Chat request

        Returns:
            Chat response
        """
        pass

    def chat_stream(self, request: ChatRequest) -> Iterator[StreamChunk]:
        """Make a synchronous streaming chat request.

        Args:
            request: Chat request with stream=True

        Yields:
            Stream chunks

        Raises:
            UnifyLLMError: If the request fails
        """
        if not request.stream:
            request.stream = True

        yield from self._chat_stream_impl(request)

    @abstractmethod
    def _chat_stream_impl(self, request: ChatRequest) -> Iterator[StreamChunk]:
        """Implementation of synchronous streaming chat request.

        Args:
            request: Chat request

        Yields:
            Stream chunks
        """
        pass

    async def achat_stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """Make an asynchronous streaming chat request.

        Args:
            request: Chat request with stream=True

        Yields:
            Stream chunks

        Raises:
            UnifyLLMError: If the request fails
        """
        if not request.stream:
            request.stream = True

        async for chunk in self._achat_stream_impl(request):
            yield chunk

    @abstractmethod
    async def _achat_stream_impl(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """Implementation of asynchronous streaming chat request.

        Args:
            request: Chat request

        Yields:
            Stream chunks
        """
        pass

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> None:
        """Handle HTTP errors and convert to appropriate exceptions.

        Args:
            error: HTTP status error

        Raises:
            UnifyLLMError: Appropriate exception based on status code
        """
        from src.core.exceptions import (
            APIError,
            AuthenticationError,
            InvalidRequestError,
            RateLimitError,
        )

        status_code = error.response.status_code
        try:
            response_data = error.response.json()
        except Exception:
            response_data = {"error": error.response.text}

        if status_code == 401:
            raise AuthenticationError(
                message=str(response_data.get("error", "Authentication failed")),
                provider=self.name,
                status_code=status_code,
                response=response_data,
            )
        elif status_code == 429:
            retry_after = error.response.headers.get("retry-after")
            raise RateLimitError(
                message=str(response_data.get("error", "Rate limit exceeded")),
                provider=self.name,
                status_code=status_code,
                response=response_data,
                retry_after=int(retry_after) if retry_after else None,
            )
        elif status_code in (400, 404, 422):
            raise InvalidRequestError(
                message=str(response_data.get("error", "Invalid request")),
                provider=self.name,
                status_code=status_code,
                response=response_data,
            )
        else:
            raise APIError(
                message=str(response_data.get("error", f"API error: {status_code}")),
                provider=self.name,
                status_code=status_code,
                response=response_data,
            )
