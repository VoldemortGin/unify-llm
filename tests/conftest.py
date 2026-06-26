# 测试门禁收集策略(Phase 3 重启后)。
# - test_basic / test_conversion_core / test_smoke / test_conformance:已随 provider 现代化纳入,
#   全部不连真网络(MockTransport / Mock / 纯转换),正常收集运行。
# - 下列仍 ignore:它们 import 仍豁免的 agent/mcp/a2a 子树(在 beartype On + filterwarnings=error
#   下会因旧式注解触发弃用告警),或依赖真 key/真网络的集成测试,留后续阶段随 agent/mcp/a2a
#   现代化后再纳入:
collect_ignore = [
    "test_agent_integration.py",  # agent 子树(仍豁免)
    "test_coverage_improvement.py",  # 顶层 import agent.tools/executor/memory(仍豁免)
    "test_mcp_a2a_databricks.py",  # mcp/a2a + 真 Databricks 凭据的集成测试
    "security",  # agent webhook/SSRF/path-traversal(仍豁免)
]
