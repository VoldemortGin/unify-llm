"""Provider adapters for various LLM services.

PEP 562 懒加载:`import unify_llm.providers` 不再急切拉起全部 provider 模块;访问某个
provider 名时才导入其模块(与顶层 unify_llm.__init__ 同构)。Phase 2 期间 9 个尚未现代化
的 provider 在 beartype On 下会触发 PEP585 弃用告警,懒加载让"只用某个已现代化 provider"
时不会把它们一并拉起。逐 provider 现代化后本 shim 可移出豁免。
"""

import importlib
from typing import Any

# 导出名 → 其所在模块。首次访问时才 import,bare `import unify_llm.providers` 保持轻量。
_LAZY_EXPORTS: dict[str, str] = {
    "BaseProvider": "unify_llm.providers.base",
    "OpenAIProvider": "unify_llm.providers.openai",
    "AnthropicProvider": "unify_llm.providers.anthropic",
    "AnthropicOpenAIProvider": "unify_llm.providers.anthropic_openai",
    "GeminiProvider": "unify_llm.providers.gemini",
    "OllamaProvider": "unify_llm.providers.ollama",
    "GrokProvider": "unify_llm.providers.grok",
    "OpenRouterProvider": "unify_llm.providers.openrouter",
    "DatabricksProvider": "unify_llm.providers.databricks",
    "QwenProvider": "unify_llm.providers.qwen",
    "ByteDanceProvider": "unify_llm.providers.bytedance",
}

__all__ = list(_LAZY_EXPORTS)


def __getattr__(name: str) -> Any:  # noqa: ANN401  PEP 562 模块级 __getattr__ 固有返回 Any
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module_name), name)
