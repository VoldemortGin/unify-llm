"""Anthropic OpenAI-compatible provider implementation."""


from __future__ import annotations

from unify_llm.providers.openai import OpenAIProvider


class AnthropicOpenAIProvider(OpenAIProvider):
    """Anthropic API provider using OpenAI-compatible endpoint.

    Anthropic provides an OpenAI-compatible API endpoint, allowing you to
    use OpenAI SDK/format to call Claude models.

    Base URL: https://api.anthropic.com/v1

    Environment variable: ANTHROPIC_API_KEY

    Note: This is different from the native Anthropic provider which uses
    the Messages API directly. Use this if you prefer OpenAI-style API.
    """

    def _get_headers(self) -> dict:
        """Get headers for Anthropic OpenAI-compatible API requests."""
        headers = {
            "Content-Type": "application/json",
        }

        if self.config.api_key:
            headers["x-api-key"] = self.config.api_key

        # Add any extra headers
        headers.update(self.config.extra_headers)

        return headers

    def _get_base_url(self) -> str:
        """Get the base URL for Anthropic OpenAI-compatible API."""
        return self.config.base_url or "https://api.anthropic.com/v1"

