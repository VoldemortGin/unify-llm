"""Databricks serving endpoints(独立 adapter)。

Databricks 暴露的是逐字段 OpenAI 兼容的 /chat/completions,转换逻辑可整段复用
OpenAICompatibleProvider。唯一差异是 base URL 取自 ``DATABRICKS_BASE_URL`` 环境变量(每个
workspace 一个,没有静态默认),故覆写 _get_base_url;鉴权仍是 Bearer。
"""

import os
from typing import override

from unify_llm.adapters.openai_compatible import OpenAICompatibleProvider, OpenAICompatSpec
from unify_llm.models import ProviderConfig

_SPEC = OpenAICompatSpec(
    name="databricks",
    base_url="",  # 无静态默认:实际 base URL 由 _get_base_url 从 config / env 解析
    env_var="DATABRICKS_API_KEY",
    default_model="databricks-claude-sonnet-4-5",
)


class DatabricksProvider(OpenAICompatibleProvider):
    """Databricks(OpenAI 兼容,base URL 来自 DATABRICKS_BASE_URL)。"""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config, _SPEC)

    @override
    def _get_base_url(self) -> str:
        """ProviderConfig.base_url 优先,否则取 DATABRICKS_BASE_URL 环境变量。"""
        if self.config.base_url:
            return self.config.base_url
        return os.getenv("DATABRICKS_BASE_URL", "")
