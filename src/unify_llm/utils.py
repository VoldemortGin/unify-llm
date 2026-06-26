"""Utility functions for UnifyLLM."""

import os
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from unify_llm.core.settings import PROJECT_ROOT

# Cache for model name mappings
_model_name_mapping: dict[str, str] | None = None


def get_model_name_mapping_path() -> Path:
    """Get the path to model_name_mapping.yaml.

    Returns:
        Path to the model name mapping configuration file (anchored at the repo root,
        not the ``src/`` package dir).
    """
    return PROJECT_ROOT / "configs" / "model_name_mapping.yaml"


def load_model_name_mapping() -> dict[str, str]:
    """Load model name mappings from configuration file.

    This mapping is specifically for OpenRouter provider.
    Format: alias -> provider/model (OpenRouter format)

    Returns:
        Dictionary of alias -> full_model_name
        (e.g., "claude-4.5" -> "anthropic/claude-sonnet-4-5-20250929").
    """
    global _model_name_mapping

    if _model_name_mapping is not None:
        return _model_name_mapping

    mapping_path = get_model_name_mapping_path()

    if not mapping_path.exists():
        _model_name_mapping = {}
        return _model_name_mapping

    with open(mapping_path, encoding="utf-8") as f:
        loaded = yaml.safe_load(f)

    _model_name_mapping = loaded if isinstance(loaded, dict) else {}
    return _model_name_mapping


def resolve_model_name(provider: str, model: str) -> str:
    """Resolve a model alias to its full name.

    For OpenRouter: uses the flat mapping from model_name_mapping.yaml
    to convert aliases like "claude-4.5" to "anthropic/claude-sonnet-4-5-20250929".

    For other providers: returns the original model name unchanged.

    Args:
        provider: Provider name (e.g., "openrouter", "openai", "anthropic")
        model: Model name or alias (e.g., "claude-4.5", "gpt5")

    Returns:
        Full model name

    Example:
        >>> resolve_model_name("openrouter", "claude-4.5")
        "anthropic/claude-sonnet-4-5-20250929"
        >>> resolve_model_name("openai", "gpt-4-turbo")  # Not OpenRouter, unchanged
        "gpt-4-turbo"
    """
    # Only apply mapping for OpenRouter
    if provider.lower() != "openrouter":
        return model

    mapping = load_model_name_mapping()

    # Return the mapped name if it exists, otherwise return original
    return mapping.get(model, model)


def reload_model_name_mapping() -> dict[str, str]:
    """Reload model name mappings from configuration file.

    Use this if you've updated the configuration file and want to
    reload without restarting.

    Returns:
        Updated dictionary of alias -> full_model_name
    """
    global _model_name_mapping
    _model_name_mapping = None
    return load_model_name_mapping()


# provider → 候选 API key 环境变量(单一来源:get_api_key_from_env / requires_api_key 共用)。
# 空列表表示该 provider 无需 key(如本地 ollama),工厂据此决定"缺 key 时是否回退/硬失败"。
ENV_VAR_MAP: dict[str, list[str]] = {
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "anthropic_openai": ["ANTHROPIC_API_KEY"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "grok": ["XAI_API_KEY", "GROK_API_KEY"],
    "ollama": [],  # Ollama doesn't need API key
    "openrouter": ["OPENROUTER_API_KEY"],
    "databricks": ["DATABRICKS_API_KEY"],
    "qwen": ["QWEN_API_KEY", "DASHSCOPE_API_KEY"],
    "bytedance": ["BYTEDANCE_API_KEY", "DOUBAO_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
}


def get_api_key_from_env(provider: str) -> str | None:
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
        - DeepSeek: DEEPSEEK_API_KEY
    """
    for env_var in ENV_VAR_MAP.get(provider.lower(), []):
        api_key = os.getenv(env_var)
        if api_key:
            return api_key

    return None


def requires_api_key(provider: str) -> bool:
    """该 provider 是否需要 API key。

    用于工厂的"缺 key"判定:无需 key 的 provider(如本地 ollama)即使没 key 也应正常装配,
    不该回退到 Mock。未知 provider 默认视为需要 key(保守)。

    Args:
        provider: Provider name.

    Returns:
        True 表示需要 key;False 表示该 provider 无需 key。
    """
    return ENV_VAR_MAP.get(provider.lower(), ["__unknown__"]) != []


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
    messages: list[dict[str, str]],
    max_tokens: int,
    preserve_system: bool = True,
) -> list[dict[str, str]]:
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
    system_messages: list[dict[str, str]] = []
    other_messages: list[dict[str, str]] = []

    for msg in messages:
        if msg.get("role") == "system" and preserve_system:
            system_messages.append(msg)
        else:
            other_messages.append(msg)

    # Calculate tokens for system messages
    system_tokens = sum(estimate_tokens(msg.get("content", "")) for msg in system_messages)

    # Calculate available tokens for other messages
    available_tokens = max_tokens - system_tokens

    # Truncate from the beginning if needed
    truncated_messages: list[dict[str, str]] = []
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
