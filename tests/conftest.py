# 测试专属 fixtures + RATCHET:存量测试依赖已移入 extras 的死重(croniter/fastapi)
# 且引用旧的顶层导出,本步从门禁收集中排除;逐模块现代化后再纳入。
# Phase 2:转换核心的行为不变由新增的 test_conversion_core.py 验证(只触达已现代化的
# models/openai/base/utils,不拉起仍豁免的 provider)。test_basic 经 client 必然 import
# 全部 9 个尚未现代化的 provider,在 beartype On 下触发 PEP585 弃用告警(filterwarnings
# =error)→ 继续 ignore,留 Phase 3 随 provider 现代化后再纳入。
collect_ignore = [
    "test_basic.py",
    "test_agent_integration.py",
    "test_coverage_improvement.py",
    "test_mcp_a2a_databricks.py",
    "security",
]
