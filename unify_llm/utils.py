"""Utility functions for UnifyLLM."""

import os
from typing import Dict, Optional


def get_api_key_from_env(provider: str) -> Optional[str]:
    """Get API key from environment variables.

    This function checks for provider-specific environment variables
    in a standardized format.

    Args:
        provider: Provider name (e.g., "openai", "anthropic")

    Returns:
        API key if found, None otherwise

    Environment variable naming convention:
        - OpenAI: OPENAI_API_KEY
        - Anthropic: ANTHROPIC_API_KEY
        - Gemini: GEMINI_API_KEY or GOOGLE_API_KEY
    """
    # Standard environment variable names for each provider
    env_var_map: Dict[str, list] = {
        "openai": ["OPENAI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY"],
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "ollama": [],  # Ollama doesn't need API key
    }

    provider_lower = provider.lower()
    env_vars = env_var_map.get(provider_lower, [])

    for env_var in env_vars:
        api_key = os.getenv(env_var)
        if api_key:
            return api_key

    return None


def estimate_tokens(text: str) -> int:
    """Rough estimation of token count.

    This is a simple approximation. For accurate token counting,
    use the provider's tokenizer.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    # Rough approximation: ~4 characters per token
    return len(text) // 4


def truncate_messages(
    messages: list,
    max_tokens: int,
    preserve_system: bool = True,
) -> list:
    """Truncate messages to fit within token limit.

    This is a simple truncation that removes oldest messages first.
    System messages are preserved by default.

    Args:
        messages: List of messages
        max_tokens: Maximum token limit
        preserve_system: Whether to preserve system messages

    Returns:
        Truncated list of messages
    """
    if not messages:
        return []

    # Separate system and other messages
    system_messages = []
    other_messages = []

    for msg in messages:
        if msg.get("role") == "system" and preserve_system:
            system_messages.append(msg)
        else:
            other_messages.append(msg)

    # Calculate tokens for system messages
    system_tokens = sum(
        estimate_tokens(msg.get("content", ""))
        for msg in system_messages
    )

    # Calculate available tokens for other messages
    available_tokens = max_tokens - system_tokens

    # Truncate from the beginning if needed
    truncated_messages = []
    current_tokens = 0

    # Add messages from the end (most recent first)
    for msg in reversed(other_messages):
        msg_tokens = estimate_tokens(msg.get("content", ""))

        if current_tokens + msg_tokens <= available_tokens:
            truncated_messages.insert(0, msg)
            current_tokens += msg_tokens
        else:
            break

    # Combine system messages and truncated messages
    return system_messages + truncated_messages


def format_provider_error(error: Exception, provider: str) -> str:
    """Format a provider error for display.

    Args:
        error: The exception
        provider: Provider name

    Returns:
        Formatted error message
    """
    error_type = error.__class__.__name__
    error_msg = str(error)

    return f"[{provider.upper()}] {error_type}: {error_msg}"
