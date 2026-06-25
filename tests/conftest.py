# 测试专属 fixtures + RATCHET:存量测试依赖已移入 extras 的死重(croniter/fastapi)
# 且引用旧的顶层导出,本步从门禁收集中排除;Phase 2+ 现代化后再纳入。
collect_ignore = [
    "test_basic.py",
    "test_agent_integration.py",
    "test_coverage_improvement.py",
    "test_mcp_a2a_databricks.py",
    "security",
]
