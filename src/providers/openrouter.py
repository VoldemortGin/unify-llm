"""OpenRouter provider implementation."""

import rootutils

ROOT_DIR = rootutils.setup_root(search_from=__file__, indicator=[".project-root"], pythonpath=True)

from src.providers.openai import OpenAIProvider


class OpenRouterProvider(OpenAIProvider):
    """OpenRouter API provider implementation.

    OpenRouter provides access to multiple LLM providers through a unified
    OpenAI-compatible API. It supports models from OpenAI, Anthropic, Google,
    Meta, and many others.

    Environment variable: OPENROUTER_API_KEY
    """

    def _get_base_url(self) -> str:
        """Get the base URL for OpenRouter API."""
        return self.config.base_url or "https://openrouter.ai/api/v1"

    def _get_headers(self) -> dict:
        """Get headers for OpenRouter API requests."""
        headers = super()._get_headers()
        # OpenRouter recommends setting these headers
        headers["HTTP-Referer"] = headers.get("HTTP-Referer", "https://github.com/unify-llm")
        headers["X-Title"] = headers.get("X-Title", "UnifyLLM")
        return headers
