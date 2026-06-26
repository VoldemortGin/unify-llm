"""Base provider abstract class + shared adapter helpers.

adapters 是 ports 的具体实现,也是唯一允许直连厂商 HTTP 的层。本模块承载所有 adapter
共用的 HTTP 管线(连接池 / 重试 / 错误分类 / 网络错归一)与两个解析小工具。
"""

import contextlib
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable, Iterator
from types import TracebackType
from typing import Self, TypeVar

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from unify_llm.core.exceptions import (
    APIError,
    AuthenticationError,
    InvalidRequestError,
    ProviderError,
    RateLimitError,
    TimeoutError,
)
from unify_llm.models import (
    ChatRequest,
    ChatResponse,
    FinishReason,
    ProviderConfig,
    StreamChunk,
)

_T = TypeVar("_T")


def to_finish_reason(
    value: object, mapping: dict[str, FinishReason] | None = None
) -> FinishReason | None:
    """把厂商私有的 finish/stop 原因安全归一为统一的 FinishReason(未知一律 None)。

    parse-don't-validate:厂商可能给出 ``end_turn`` / ``OTHER`` / ``null`` 等不在统一枚举里的
    值;直接塞进 ``FinishReason`` 字段会 ValidationError。本函数先查 ``mapping``,再尝试枚举字面
    值,二者皆不中则返回 None,绝不抛。

    Args:
        value: 厂商响应里的原始原因(任意类型,容错处理)。
        mapping: 厂商私有原因 → 统一 FinishReason 的映射(可选)。

    Returns:
        归一后的 FinishReason,或 None。
    """
    if not isinstance(value, str) or not value:
        return None
    if mapping is not None and value in mapping:
        return mapping[value]
    try:
        return FinishReason(value)
    except ValueError:
        return None


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

    def __init__(
        self,
        config: ProviderConfig,
        *,
        client: httpx.Client | None = None,
        async_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            config: Provider configuration.
            client: Optional injected sync HTTP client (e.g. a process-wide shared client).
                When provided it is NOT owned by this provider (the injector closes it);
                when omitted a private client is self-built and owned.
            async_client: Optional injected async HTTP client (same ownership semantics).
        """
        self.config = config
        self.name = self.__class__.__name__.replace("Provider", "").lower()

        # Create HTTP clients with connection pooling (only for the self-built ones).
        timeout = httpx.Timeout(connect=5.0, read=self.config.timeout, write=10.0, pool=5.0)
        headers = self._get_headers()
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0,
        )

        if client is not None:
            self.client = client
            self._owns_client = False
        else:
            self.client = httpx.Client(timeout=timeout, headers=headers, limits=limits)
            self._owns_client = True

        if async_client is not None:
            self.async_client = async_client
            self._owns_async_client = False
        else:
            self.async_client = httpx.AsyncClient(timeout=timeout, headers=headers, limits=limits)
            self._owns_async_client = True

    def __del__(self) -> None:
        """Best-effort close of the OWNED sync client only (ADR-10).

        Deliberately never touches the async client and never runs an event loop: the
        previous ``asyncio.run(self.async_client.aclose())`` exploded when GC happened
        inside a long-lived loop (e.g. the gateway). httpx 0.28 ``AsyncClient`` has no
        ``__del__`` and emits no ``ResourceWarning`` when an unused client is GC'd, so
        abandoning an owned async client here is safe. An injected/shared client is owned
        by its injector and must not be closed here.
        """
        if getattr(self, "_owns_client", False):
            with contextlib.suppress(Exception):
                self.client.close()

    def close(self) -> None:
        """Close the sync HTTP client if this provider owns it."""
        if self._owns_client:
            self.client.close()

    async def aclose(self) -> None:
        """Close the async HTTP client if this provider owns it."""
        if self._owns_async_client:
            await self.async_client.aclose()

    def __enter__(self) -> Self:
        """Sync context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Sync context manager exit (closes the sync client only if owned)."""
        if self._owns_client:
            self.client.close()

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit (closes the async client only if owned)."""
        if self._owns_async_client:
            await self.async_client.aclose()

    @abstractmethod
    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests.

        Returns:
            Dictionary of headers
        """

    @abstractmethod
    def _get_base_url(self) -> str:
        """Get the base URL for API requests.

        Returns:
            Base URL string
        """

    @abstractmethod
    def _convert_request(self, request: ChatRequest) -> dict[str, object]:
        """Convert a ChatRequest to provider-specific format.

        Args:
            request: Unified chat request

        Returns:
            Provider-specific request dictionary
        """

    @abstractmethod
    def _convert_response(self, response: dict[str, object]) -> ChatResponse:
        """Convert provider-specific response to ChatResponse.

        Args:
            response: Provider-specific response dictionary

        Returns:
            Unified chat response
        """

    @abstractmethod
    def _convert_stream_chunk(self, chunk: dict[str, object]) -> StreamChunk | None:
        """Convert provider-specific stream chunk to StreamChunk.

        Args:
            chunk: Provider-specific chunk dictionary

        Returns:
            Unified stream chunk, or None if chunk should be skipped
        """

    def _with_retry(self, func: Callable[[ChatRequest], _T]) -> Callable[[ChatRequest], _T]:
        """Wrap a request implementation with the configured retry policy.

        Args:
            func: The (sync or async) request implementation to wrap.

        Returns:
            The wrapped callable, preserving the original call/return type.
        """
        decorator = retry(
            stop=stop_after_attempt(self.config.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((RateLimitError, TimeoutError, APIError)),
            reraise=True,
        )
        return decorator(func)

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

        return self._with_retry(self._chat_impl)(request)

    @abstractmethod
    def _chat_impl(self, request: ChatRequest) -> ChatResponse:
        """Implementation of synchronous chat request.

        Args:
            request: Chat request

        Returns:
            Chat response
        """

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

        return await self._with_retry(self._achat_impl)(request)

    @abstractmethod
    async def _achat_impl(self, request: ChatRequest) -> ChatResponse:
        """Implementation of asynchronous chat request.

        Args:
            request: Chat request

        Returns:
            Chat response
        """

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
    def _achat_stream_impl(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """Implementation of asynchronous streaming chat request.

        Args:
            request: Chat request

        Yields:
            Stream chunks
        """

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> None:
        """Handle HTTP errors and convert to appropriate exceptions.

        Args:
            error: HTTP status error

        Raises:
            UnifyLLMError: Appropriate exception based on status code
        """
        status_code = error.response.status_code
        response_data: dict[str, object]
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

    def _network_error(self, error: httpx.RequestError) -> ProviderError:
        """归一厂商网络错(ConnectError/DNS/读写失败等)为 ProviderError。

        超时(httpx.TimeoutException)由各 adapter 单独映射为 TimeoutError;HTTP 状态码错由
        ``_handle_http_error`` 分类。本方法只兜底其余传输层错误,让 exceptions.ProviderError
        真正被抛出而非形同虚设。

        Args:
            error: httpx 传输层错误(非超时、非状态码)。

        Returns:
            归一后的 ProviderError(调用方负责 ``raise ... from error``)。
        """
        return ProviderError(
            message=f"Network error while contacting {self.name}: {error}",
            provider=self.name,
        )
