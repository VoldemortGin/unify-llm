"""xAI Grok provider implementation."""

from src.providers.openai import OpenAIProvider


class GrokProvider(OpenAIProvider):
    """xAI Grok API provider implementation.

    Grok uses an OpenAI-compatible API, so we inherit from OpenAIProvider
    and only override the necessary methods.

    Supports Grok-4, Grok-3, and other xAI models.

    Environment variable: XAI_API_KEY
    """

    def _get_headers(self) -> dict:
        """Get headers for xAI Grok API requests."""
        headers = {
            "Content-Type": "application/json",
        }

        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        # Add any extra headers
        headers.update(self.config.extra_headers)

        return headers

    def _get_base_url(self) -> str:
        """Get the base URL for xAI Grok API."""
        return self.config.base_url or "https://api.x.ai/v1"

