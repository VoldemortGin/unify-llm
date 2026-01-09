# 使用 Databricks 测试 AI Agent 功能

## 📋 前提条件

### 1. Databricks 配置

你需要以下信息：

```bash
# Databricks workspace URL
export DATABRICKS_BASE_URL="https://your-workspace.cloud.databricks.com"

# Databricks personal access token
export DATABRICKS_API_KEY="dapi..."

# 或者在代码中指定
```

### 2. 部署模型端点

在 Databricks 中，你需要先部署一个模型端点：

1. 在 Databricks workspace 中进入 "Serving"
2. 创建一个 serving endpoint
3. 选择模型（如 Meta Llama 3）
4. 记下端点名称（例如：`databricks-meta-llama-3-1-70b-instruct`）

## 🚀 快速开始

### 基础测试（不使用 Agent）

```python
from src import UnifyLLM

# 方式 1: 使用环境变量
client = UnifyLLM(
    provider="databricks",
    api_key="dapi...",
    base_url="https://your-workspace.cloud.databricks.com"
)

# 方式 2: 自动从环境变量读取
# export DATABRICKS_API_KEY="dapi..."
# export DATABRICKS_BASE_URL="https://..."
client = UnifyLLM(provider="databricks")

# 测试调用
response = client.chat(
    model="databricks-meta-llama-3-1-70b-instruct",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.content)
```

### 使用 AI Agent

```python
from src import UnifyLLM
from src.agent import (
    Agent,
    AgentConfig,
    AgentType,
    AgentExecutor,
    ToolRegistry,
)
from src.agent.builtin_tools import create_calculator_tool

# 1. 初始化 Databricks 客户端
client = UnifyLLM(
    provider="databricks",
    api_key="your-databricks-token",
    base_url="https://your-workspace.cloud.databricks.com"
)

# 2. 注册工具
registry = ToolRegistry()
registry.register(create_calculator_tool())

# 3. 创建 Agent 配置
config = AgentConfig(
    name="databricks_agent",
    agent_type=AgentType.TOOLS,
    model="databricks-meta-llama-3-1-70b-instruct",
    provider="databricks",
    system_prompt="You are a helpful assistant with access to tools.",
    tools=["calculator"],
    temperature=0,
    max_iterations=3
)

# 4. 创建并运行 Agent
agent = Agent(config=config, client=client)
executor = AgentExecutor(agent=agent, tool_registry=registry)

result = executor.run("What is 15 * 23?")
print(result.output)
```

### 使用 n8n 风格自动化

```python
from src import UnifyLLM
from src.agent import (
    Agent, AgentConfig, AgentExecutor, ToolRegistry,
    ScheduleTrigger, TriggerConfig, TriggerType,
    ExecutionHistory, ExecutionData, ExecutionStatus,
    create_http_request_tool,
)
from datetime import datetime

# 初始化
client = UnifyLLM(provider="databricks", api_key="...", base_url="...")
history = ExecutionHistory(db_path="databricks_executions.db")

# 创建带 HTTP 工具的 Agent
registry = ToolRegistry()
registry.register(create_http_request_tool())

config = AgentConfig(
    name="api_agent",
    agent_type=AgentType.TOOLS,
    model="databricks-meta-llama-3-1-70b-instruct",
    provider="databricks",
    tools=["http_request"]
)

agent = Agent(config=config, client=client)
executor = AgentExecutor(agent=agent, tool_registry=registry)


# 定义自动化工作流
def automated_workflow(event):
    execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"🤖 Workflow triggered: {execution_id}")

    # 记录开始
    execution = ExecutionData(
        id=execution_id,
        workflow_id=event.metadata["workflow_id"],
        workflow_name="API Monitor",
        status=ExecutionStatus.RUNNING,
        start_time=datetime.now(),
        trigger_type=event.trigger_type.value,
        input_data=event.data
    )
    history.save(execution)

    try:
        # 运行 Agent
        result = executor.run(
            "Fetch the GitHub API status from https://www.githubstatus.com/api/v2/status.json "
            "and tell me if everything is operational."
        )

        # 记录成功
        execution.status = ExecutionStatus.SUCCESS
        execution.end_time = datetime.now()
        execution.output_data = {"result": result.output}
        history.save(execution)

        print(f"✅ Success: {result.output}")

    except Exception as e:
        # 记录失败
        execution.status = ExecutionStatus.ERROR
        execution.end_time = datetime.now()
        execution.error = str(e)
        history.save(execution)

        print(f"❌ Error: {e}")


# 创建定时触发器（每小时运行）
trigger_config = TriggerConfig(
    id="hourly_api_check",
    name="Hourly API Health Check",
    type=TriggerType.SCHEDULE,
    workflow_id="api_monitor",
    config={"cron": "0 * * * *"}  # 每小时
)

trigger = ScheduleTrigger(trigger_config, automated_workflow)
await trigger.start()

# 工作流会每小时自动运行！
```

## 🎯 测试示例

运行我创建的测试文件：

```bash
# 设置环境变量
export DATABRICKS_API_KEY="your-token"
export DATABRICKS_BASE_URL="https://your-workspace.cloud.databricks.com"

# 运行测试
python examples/test_agent_databricks.py
```

## ⚠️ 常见问题

### 1. 404 Not Found 错误

**问题**: `404 Not Found for url '.../serving-endpoints/chat/completions'`

**原因**: 端点路径不正确

**解决**:
- 确保你的 Databricks workspace 已部署模型端点
- 使用正确的模型名称（与你的 serving endpoint 名称匹配）
- 检查 `base_url` 是否正确

### 2. 401 Unauthorized 错误

**问题**: 认证失败

**解决**:
- 检查 `DATABRICKS_API_KEY` 是否正确
- 确保 token 有权访问 serving endpoints
- 在 Databricks 设置中生成新的 personal access token

### 3. 模型名称不匹配

**问题**: 模型不存在

**解决**:
- 在 Databricks UI 中检查你的 serving endpoint 名称
- 更新代码中的 `model` 参数为正确的端点名称

## 📚 支持的功能

使用 Databricks 时，以下 AI Agent 功能都可用：

✅ **核心 Agent**
- Tools Agent
- Conversational Agent
- Agent Templates

✅ **工具系统**
- 20+ 内置工具
- HTTP Request 工具
- 自定义工具

✅ **n8n 风格自动化**
- Schedule Triggers
- Webhook Triggers
- Interval Triggers
- Manual Triggers

✅ **工作流编排**
- Sequential execution
- Parallel execution
- Conditional branching

✅ **执行历史**
- SQLite 持久化
- 执行统计
- 错误追踪

## 🔧 调试建议

如果遇到问题，可以启用详细日志：

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# 现在会看到所有 API 调用的详细信息
```

## 📝 完整示例

查看以下文件获取完整示例：

- `examples/test_agent_databricks.py` - Databricks Agent 测试
- `examples/agent_n8n_style.py` - n8n 风格自动化示例
- `docs/N8N_STYLE_FEATURES.md` - 完整功能文档

---

**注意**: 确保你的 Databricks workspace 已正确配置并部署了模型端点，否则测试将无法运行。
