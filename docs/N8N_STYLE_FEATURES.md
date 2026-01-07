# UnifyLLM - n8n风格 AI Agent 功能总结

## 🎉 项目现状

UnifyLLM 现在是一个**功能完整的 n8n 风格 AI Agent 自动化平台**！

## ✨ 新增的 n8n 风格功能

### 1. ⏰ 触发器系统 (Triggers)

类似 n8n 的触发器，支持多种自动化启动方式：

#### 可用触发器类型：

- **ScheduleTrigger** - 基于 Cron 的定时触发器
  ```python
  from unify_llm.agent import ScheduleTrigger, TriggerConfig, TriggerType

  config = TriggerConfig(
      id="daily_report",
      name="Daily Report",
      type=TriggerType.SCHEDULE,
      workflow_id="report_workflow",
      config={"cron": "0 9 * * *"}  # 每天早上9点
  )

  trigger = ScheduleTrigger(config, callback_function)
  await trigger.start()
  ```

- **IntervalTrigger** - 固定间隔触发器
  ```python
  config = TriggerConfig(
      id="check_every_5min",
      name="Check Every 5 Minutes",
      type=TriggerType.INTERVAL,
      workflow_id="monitor_workflow",
      config={"interval_seconds": 300}
  )

  trigger = IntervalTrigger(config, callback_function)
  await trigger.start()
  ```

- **WebhookTrigger** - HTTP Webhook 触发器
  ```python
  config = TriggerConfig(
      id="api_webhook",
      name="API Events",
      type=TriggerType.WEBHOOK,
      workflow_id="event_workflow",
      config={"path": "/webhook/events", "method": "POST"}
  )

  trigger = WebhookTrigger(config, callback_function)
  ```

- **ManualTrigger** - 手动触发器
  ```python
  config = TriggerConfig(
      id="manual_exec",
      name="Manual Execution",
      type=TriggerType.MANUAL,
      workflow_id="test_workflow"
  )

  trigger = ManualTrigger(config, callback_function)
  trigger.execute({"param": "value"})
  ```

#### 触发器管理器：

```python
from unify_llm.agent import TriggerManager

manager = TriggerManager()
manager.add_trigger(schedule_trigger)
manager.add_trigger(webhook_trigger)

# 启动所有触发器
await manager.start_all()

# 获取状态
status = manager.get_status()
```

### 2. 🌐 HTTP 请求节点 (HTTP Request Node)

类似 n8n 的 HTTP Request 节点，支持完整的 REST API 调用：

```python
from unify_llm.agent import http_request, http_get, http_post

# GET 请求
result = await http_get(
    url="https://api.github.com/repos/microsoft/vscode",
    headers={"Accept": "application/json"}
)

# POST 请求
result = await http_post(
    url="https://api.example.com/users",
    body={"name": "John", "email": "john@example.com"}
)

# 带认证的请求
result = await http_request(
    url="https://api.example.com/protected",
    method="GET",
    auth_type="bearer",
    auth_token="your-token"
)

# 支持的认证方式
# - none: 无认证
# - basic: Basic Auth
# - bearer: Bearer Token
# - api_key: API Key
```

**作为 Agent 工具使用：**

```python
from unify_llm.agent import create_http_request_tool, ToolRegistry

registry = ToolRegistry()
http_tool = create_http_request_tool()
registry.register(http_tool)

# Agent 现在可以调用 HTTP API 了！
```

### 3. 🔗 Webhook 服务器 (Webhook Server)

内置的 Webhook 服务器，接收 HTTP 请求并触发工作流：

```python
from unify_llm.agent import WebhookServer, WebhookTrigger

# 创建 Webhook 服务器
server = WebhookServer(host="0.0.0.0", port=5678)

# 注册 Webhook
webhook = WebhookTrigger(config, callback_function)
server.register_webhook(webhook)

# 启动服务器
await server.start()

# 服务器现在监听: http://0.0.0.0:5678/webhook/your-path
```

**功能：**
- ✅ 多 Webhook 支持
- ✅ 支持所有 HTTP 方法 (GET, POST, PUT, DELETE, PATCH)
- ✅ 自动解析 JSON body
- ✅ 健康检查端点 `/health`
- ✅ Webhook 列表端点 `/webhooks`

**测试 Webhook：**

```python
from unify_llm.agent import WebhookClient

client = WebhookClient(base_url="http://localhost:5678")

# 发送 webhook
response = await client.send_webhook(
    path="/webhook/test",
    method="POST",
    data={"message": "Hello!"}
)

# 查看所有 webhooks
webhooks = await client.list_webhooks()
```

### 4. 📊 执行历史和持久化 (Execution History)

类似 n8n 的执行历史功能，使用 SQLite 持久化存储：

```python
from unify_llm.agent import ExecutionHistory, ExecutionData, ExecutionStatus
from datetime import datetime

# 初始化
history = ExecutionHistory(db_path="executions.db")

# 保存执行记录
execution = ExecutionData(
    id="exec_123",
    workflow_id="workflow_1",
    workflow_name="Daily Report",
    status=ExecutionStatus.SUCCESS,
    start_time=datetime.now(),
    end_time=datetime.now(),
    trigger_type="schedule",
    input_data={"date": "2024-01-01"},
    output_data={"report": "success"}
)

history.save(execution)

# 查询执行历史
recent = history.get_recent(limit=10)
by_workflow = history.get_by_workflow("workflow_1", limit=20)
by_status = history.get_recent(status="error", limit=5)

# 获取统计数据
stats = history.get_statistics(workflow_id="workflow_1")
# {
#   "total": 100,
#   "success": 85,
#   "error": 15,
#   "running": 0,
#   "success_rate": 85.0
# }

# 清理旧数据
deleted = history.delete_old(days=30)  # 删除30天前的记录
```

## 📦 完整的模块结构

```
unify_llm/agent/
├── 原有核心模块 (12个)
│   ├── base.py           - Agent 基础
│   ├── tools.py          - 工具系统
│   ├── memory.py         - 记忆管理
│   ├── executor.py       - 执行器
│   ├── workflow.py       - 工作流编排
│   ├── builtin_tools.py  - 内置工具
│   ├── extended_tools.py - 扩展工具
│   ├── advanced.py       - 高级功能
│   ├── templates.py      - Agent 模板
│   ├── visualization.py  - 可视化
│   ├── monitoring.py     - 监控
│   └── __init__.py       - 模块导出
│
└── 新增 n8n 风格模块 (4个)
    ├── triggers.py          - 触发器系统 ⭐
    ├── http_tools.py        - HTTP 请求工具 ⭐
    ├── webhook_server.py    - Webhook 服务器 ⭐
    └── execution_history.py - 执行历史 ⭐

总计: 16 个模块, 6,500+ 行代码
```

## 🚀 完整的自动化示例

```python
from unify_llm.agent import (
    ScheduleTrigger, TriggerConfig, TriggerType,
    http_get, ExecutionHistory, ExecutionData, ExecutionStatus
)
from datetime import datetime

# 1. 初始化执行历史
history = ExecutionHistory()

# 2. 定义工作流逻辑
async def monitor_github(event):
    """监控 GitHub 仓库"""
    execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 记录开始
    execution = ExecutionData(
        id=execution_id,
        workflow_id="github_monitor",
        workflow_name="GitHub Issue Monitor",
        status=ExecutionStatus.RUNNING,
        start_time=datetime.now(),
        trigger_type=event.trigger_type.value,
        input_data=event.data
    )
    history.save(execution)

    try:
        # 调用 GitHub API
        result = await http_get(
            url="https://api.github.com/repos/microsoft/vscode/issues",
            query_params={"state": "open", "per_page": "5"}
        )

        if result.success:
            issues = result.output["body"]

            # 记录成功
            execution.status = ExecutionStatus.SUCCESS
            execution.end_time = datetime.now()
            execution.output_data = {"issues_count": len(issues)}
            history.save(execution)

            print(f"✅ Found {len(issues)} open issues")
        else:
            raise Exception(result.error)

    except Exception as e:
        # 记录失败
        execution.status = ExecutionStatus.ERROR
        execution.end_time = datetime.now()
        execution.error = str(e)
        history.save(execution)
        print(f"❌ Error: {e}")

# 3. 创建定时触发器 (每小时执行)
config = TriggerConfig(
    id="hourly_github_check",
    name="Hourly GitHub Check",
    type=TriggerType.SCHEDULE,
    workflow_id="github_monitor",
    config={"cron": "0 * * * *"}
)

trigger = ScheduleTrigger(config, monitor_github)
await trigger.start()

# 工作流现在会每小时自动运行，并记录所有执行历史！
```

## 📈 与 n8n 的功能对比

| 功能 | n8n | UnifyLLM | 说明 |
|------|-----|----------|------|
| **触发器** |
| Cron 定时触发 | ✅ | ✅ | 完全兼容 cron 表达式 |
| 固定间隔触发 | ✅ | ✅ | 支持秒级间隔 |
| Webhook 触发 | ✅ | ✅ | HTTP 端点触发 |
| 手动触发 | ✅ | ✅ | 按需执行 |
| **节点/工具** |
| HTTP Request | ✅ | ✅ | 支持所有 HTTP 方法 |
| 自定义函数 | ✅ | ✅ | Python 函数作为工具 |
| **工作流** |
| 顺序执行 | ✅ | ✅ | Sequential 节点 |
| 并行执行 | ✅ | ✅ | Parallel 节点 |
| 条件分支 | ✅ | ✅ | Condition 节点 |
| Human-in-Loop | ✅ | ✅ | 人工介入节点 |
| **执行管理** |
| 执行历史 | ✅ | ✅ | SQLite 持久化 |
| 执行统计 | ✅ | ✅ | 成功率、错误率等 |
| 错误处理 | ✅ | ✅ | 自动重试、错误捕获 |
| **其他** |
| Web UI | ✅ | ❌ | n8n 有可视化界面 |
| Python API | 有限 | ✅ | UnifyLLM 完整 Python API |
| AI Agent | 有限 | ✅ | UnifyLLM 原生 AI Agent |

## 💡 使用场景

### 1. 定时数据同步
```python
# 每天凌晨同步数据
config = TriggerConfig(
    id="daily_sync",
    name="Daily Data Sync",
    type=TriggerType.SCHEDULE,
    workflow_id="sync_workflow",
    config={"cron": "0 0 * * *"}
)
```

### 2. API 监控告警
```python
# 每5分钟检查 API 健康状态
config = TriggerConfig(
    id="api_health_check",
    name="API Health Monitor",
    type=TriggerType.INTERVAL,
    workflow_id="health_check",
    config={"interval_seconds": 300}
)
```

### 3. Webhook 事件处理
```python
# 接收 GitHub webhook 事件
server = WebhookServer(port=5678)
server.register_webhook(github_webhook)
await server.start()
```

### 4. 数据管道自动化
```python
# 1. 触发器启动
# 2. HTTP 调用外部 API
# 3. Agent 处理数据
# 4. 保存执行历史
# 5. 错误自动重试
```

## 📚 示例和文档

- `examples/agent_n8n_style.py` - 完整的 n8n 风格功能演示
- `examples/agent_basic.py` - 基础 Agent 使用
- `examples/agent_workflow.py` - 工作流示例
- `examples/agent_advanced.py` - 高级功能示例
- `docs/AI_AGENT_GUIDE.md` - 完整指南
- `docs/AI_AGENT_QUICK_REF.md` - 快速参考

## 🎯 总结

UnifyLLM 现在提供：

✅ **完整的 n8n 风格自动化功能**
- 4 种触发器类型
- HTTP 请求节点
- Webhook 服务器
- 执行历史持久化

✅ **强大的 AI Agent 能力**
- 4 种 Agent 类型
- 20+ 内置工具
- 工作流编排
- 记忆管理

✅ **企业级特性**
- 错误处理和重试
- 性能监控
- 可视化
- 完整的执行历史

🚀 **立即开始使用：**

```bash
pip install -e .
python examples/agent_n8n_style.py
```

---

**UnifyLLM - 让 AI Agent 自动化更简单！** 🎉
