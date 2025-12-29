"""Exception definitions for UnifyLLM."""

from typing import Any, Dict, Optional


class UnifyLLMError(Exception):
    """Base exception for all UnifyLLM errors.

    Attributes:
        message: Error message
        provider: The provider that raised the error
        status_code: HTTP status code (if applicable)
        response: Raw response from the provider (if available)
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

    def __str__(self) -> str:
        """String representation of the error."""
        parts = [self.message]
        if self.provider:
            parts.append(f"(provider: {self.provider})")
        if self.status_code:
            parts.append(f"(status: {self.status_code})")
        return " ".join(parts)


class AuthenticationError(UnifyLLMError):
    """Raised when authentication fails.

    This typically indicates:
    - Missing API key
    - Invalid API key
    - Expired API key
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        provider: Optional[str] = None,
        status_code: Optional[int] = 401,
        response: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, provider, status_code, response)


class RateLimitError(UnifyLLMError):
    """Raised when rate limit is exceeded.

    This indicates that too many requests have been made in a short period.
    The client should retry after a delay.

    Attributes:
        retry_after: Suggested time to wait before retrying (in seconds)
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        provider: Optional[str] = None,
        status_code: Optional[int] = 429,
        response: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message, provider, status_code, response)
        self.retry_after = retry_after


class InvalidRequestError(UnifyLLMError):
    """Raised when the request is invalid.

    This typically indicates:
    - Invalid parameters
    - Invalid model name
    - Invalid message format
    - Validation errors
    """

    def __init__(
        self,
        message: str = "Invalid request",
        provider: Optional[str] = None,
        status_code: Optional[int] = 400,
        response: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, provider, status_code, response)


class APIError(UnifyLLMError):
    """Raised when the API returns an error.

    This is a general error for API-related issues that don't fall into
    other specific categories.
    """

    def __init__(
        self,
        message: str = "API error occurred",
        provider: Optional[str] = None,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, provider, status_code, response)


class TimeoutError(UnifyLLMError):
    """Raised when a request times out.

    This indicates that the request took too long to complete.
    """

    def __init__(
        self,
        message: str = "Request timed out",
        provider: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, provider, status_code=408, response=response)


class ModelNotFoundError(InvalidRequestError):
    """Raised when the specified model is not found or not available.

    Attributes:
        model: The model name that was not found
    """

    def __init__(
        self,
        model: str,
        provider: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
    ):
        self.model = model
        message = f"Model '{model}' not found or not available"
        super().__init__(message, provider, status_code=404, response=response)


class ContentFilterError(UnifyLLMError):
    """Raised when content is filtered by the provider's content policy.

    This typically indicates that the request or response violated
    the provider's content policy.
    """

    def __init__(
        self,
        message: str = "Content filtered by provider policy",
        provider: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, provider, status_code=400, response=response)


class ProviderError(UnifyLLMError):
    """Raised when there's a provider-specific error.

    This is used for errors that are specific to a provider and don't
    fit into the standard error categories.
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, provider, status_code, response)
