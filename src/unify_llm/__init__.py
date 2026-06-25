"""UnifyLLM 包初始化:在导入任何子模块前,按配置安装 beartype 运行时类型检查。

claw hook 只对其安装之后导入的模块生效,所以本文件必须最先执行;hook 之前只能
导入 settings(叶子,本身不被检查)。核心符号在 hook 之后通过 PEP 562 懒加载暴露,
避免 `import unify_llm` 拉起 providers 等重模块;agent/mcp/a2a 不再自动导出,
需显式 `import unify_llm.agent` / `unify_llm.mcp` / `unify_llm.a2a` 按需使用。
"""

import os
from typing import Any

from unify_llm.core.settings import settings  # 叶子;有意在 hook 前导入(本身不被检查)

if settings.beartype_on:
    from beartype import BeartypeConf, BeartypeStrategy
    from beartype.claw import beartype_this_package

    # CI:全量 On 抓干净;本地:O1 抽样保持快反馈
    _strategy = BeartypeStrategy.On if os.getenv("CI") else BeartypeStrategy.O1
    beartype_this_package(conf=BeartypeConf(strategy=_strategy))

# ── 以下一律在 hook 之后 ──
__version__ = "0.1.1"

# 核心符号 → (模块, 属性):首次访问时才导入,bare `import unify_llm` 保持轻量。
_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "UnifyLLM": ("unify_llm.client", "UnifyLLM"),
    "Message": ("unify_llm.models", "Message"),
    "ChatRequest": ("unify_llm.models", "ChatRequest"),
    "ChatResponse": ("unify_llm.models", "ChatResponse"),
    "ChatResponseChoice": ("unify_llm.models", "ChatResponseChoice"),
    "StreamChunk": ("unify_llm.models", "StreamChunk"),
    "StreamChoiceDelta": ("unify_llm.models", "StreamChoiceDelta"),
    "MessageDelta": ("unify_llm.models", "MessageDelta"),
    "Usage": ("unify_llm.models", "Usage"),
    "ProviderConfig": ("unify_llm.models", "ProviderConfig"),
    "UnifyLLMError": ("unify_llm.core.exceptions", "UnifyLLMError"),
    "AuthenticationError": ("unify_llm.core.exceptions", "AuthenticationError"),
    "RateLimitError": ("unify_llm.core.exceptions", "RateLimitError"),
    "InvalidRequestError": ("unify_llm.core.exceptions", "InvalidRequestError"),
    "APIError": ("unify_llm.core.exceptions", "APIError"),
    "TimeoutError": ("unify_llm.core.exceptions", "TimeoutError"),
    "ModelNotFoundError": ("unify_llm.core.exceptions", "ModelNotFoundError"),
    "ContentFilterError": ("unify_llm.core.exceptions", "ContentFilterError"),
    "ProviderError": ("unify_llm.core.exceptions", "ProviderError"),
    "get_api_key_from_env": ("unify_llm.utils", "get_api_key_from_env"),
    "estimate_tokens": ("unify_llm.utils", "estimate_tokens"),
    "truncate_messages": ("unify_llm.utils", "truncate_messages"),
    "format_provider_error": ("unify_llm.utils", "format_provider_error"),
}

__all__ = ["__version__", *_LAZY_EXPORTS]


def __getattr__(name: str) -> Any:  # noqa: ANN401  PEP 562 模块级 __getattr__ 固有返回 Any
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    module_name, attr = target
    return getattr(importlib.import_module(module_name), attr)
