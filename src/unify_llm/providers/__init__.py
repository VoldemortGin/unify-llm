"""向后兼容门面:provider 实现已迁入 ``unify_llm.adapters``,本包仅做懒加载再导出。

历史代码/README 仍可 ``from unify_llm.providers import BaseProvider, OpenAIProvider`` 等;实际类
现居 ``unify_llm.adapters.*``。PEP 562 懒加载:``import unify_llm.providers`` 不会急切拉起全部
adapter,访问某个名字时才导入其所在模块。
"""

import importlib
from typing import Any

# 导出名 → 其所在 adapters 模块。首次访问时才 import。
_LAZY_EXPORTS: dict[str, str] = {
    "BaseProvider": "unify_llm.adapters.base",
    "OpenAIProvider": "unify_llm.adapters.openai_compatible",
    "GrokProvider": "unify_llm.adapters.openai_compatible",
    "OpenRouterProvider": "unify_llm.adapters.openai_compatible",
    "ByteDanceProvider": "unify_llm.adapters.openai_compatible",
    "DeepSeekProvider": "unify_llm.adapters.openai_compatible",
    "AnthropicProvider": "unify_llm.adapters.anthropic",
    "AnthropicOpenAIProvider": "unify_llm.adapters.anthropic_openai",
    "GeminiProvider": "unify_llm.adapters.gemini",
    "OllamaProvider": "unify_llm.adapters.ollama",
    "DatabricksProvider": "unify_llm.adapters.databricks",
    "QwenProvider": "unify_llm.adapters.qwen",
}

__all__ = list(_LAZY_EXPORTS)


def __getattr__(name: str) -> Any:  # noqa: ANN401  PEP 562 模块级 __getattr__ 固有返回 Any
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module_name), name)
