# AI Agent Framework - Complete Guide

UnifyLLM 的 AI Agent 框架提供了强大的自动化和工作流编排能力，灵感来自 n8n 的设计理念。

## 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [Agent 类型](#agent-类型)
4. [工具系统](#工具系统)
5. [记忆管理](#记忆管理)
6. [工作流编排](#工作流编排)
7. [高级用法](#高级用法)
8. [最佳实践](#最佳实践)

## 快速开始

### 创建一个简单的 Agent

```python
from src import UnifyLLM, Agent, AgentConfig, AgentExecutor, ToolRegistry
from src.agent.builtin_tools import create_calculator_tool

# 1. 初始化 LLM 客户端
client = UnifyLLM(provider="openai", api_key="sk-...")

# 2. 创建工具注册表
registry = ToolRegistry()
registry.register(create_calculator_tool())

# 3. 配置 Agent
config = AgentConfig(
    name="math_assistant",
    model="gpt-4",
    provider="openai",
    system_prompt="You are a helpful math assistant with access to a calculator.",
    tools=["calculator"],
    max_iterations=5
)

# 4. 创建 Agent 和执行器
agent = Agent(config=config, client=client)
executor = AgentExecutor(agent=agent, tool_registry=registry, verbose=True)

# 5. 运行 Agent
result = executor.run("What is the square root of 144 plus 25?")
print(result.output)
print(f"Tool calls made: {len(result.tool_calls)}")
```

## 核心概念

### 1. Agent (智能代理)

Agent 是一个自主的 AI 实体，能够：
- 理解用户输入
- 推理和规划
- 选择和使用工具
- 管理对话历史
- 与其他 Agent 协作

#### Agent 配置

```python
from src.agent import AgentConfig, AgentType

config = AgentConfig(
    name="my_agent",  # Agent 名称
    agent_type=AgentType.TOOLS,  # Agent 类型
    model="gpt-4",  # 使用的模型
    provider="openai",  # LLM 提供商
    system_prompt="...",  # 系统提示词
    temperature=0.7,  # 采样温度
    max_tokens=1000,  # 最大生成 tokens
    max_iterations=10,  # 最大迭代次数
    enable_memory=True,  # 启用记忆
    memory_window=10,  # 记忆窗口大小
    tools=["tool1", "tool2"],  # 可用工具列表
)
```

### 2. Tools (工具)

工具是 Agent 可以调用的函数，用于执行特定任务或获取信息。

#### 创建自定义工具

```python
from src.agent import Tool, ToolParameter, ToolParameterType, ToolResult


def search_web(query: str, num_results: int = 5) -> ToolResult:
    """搜索网络（示例）"""
    # 实际搜索逻辑
    results = perform_search(query, num_results)
    return ToolResult(
        success=True,
        output=results,
        metadata={"query": query, "count": len(results)}
    )


# 定义工具
search_tool = Tool(
    name="search_web",
    description="Search the web for information",
    parameters={
        "query": ToolParameter(
            type=ToolParameterType.STRING,
            description="Search query",
            required=True
        ),
        "num_results": ToolParameter(
            type=ToolParameterType.INTEGER,
            description="Number of results to return",
            required=False,
            default=5
        )
    },
    function=search_web
)

# 注册工具
registry = ToolRegistry()
registry.register(search_tool)
```

#### 自动参数检测

```python
def my_function(text: str, count: int, flag: bool = False):
    return f"Processed {text} {count} times"

# 自动检测参数
registry.register_function(
    name="my_tool",
    description="Process text multiple times",
    function=my_function
)
```

### 3. Memory (记忆)

#### ConversationMemory - 对话记忆

```python
from src.agent import ConversationMemory

# 创建记忆（保留最近 10 条消息）
memory = ConversationMemory(window_size=10)

# 添加消息
memory.add_user_message("Hello!")
memory.add_assistant_message("Hi! How can I help?")
memory.add_user_message("What's the weather?")

# 获取消息列表
messages = memory.get_messages()

# 获取最近 N 条消息
recent = memory.get_recent_messages(5)

# 清空记忆
memory.clear()
```

#### SharedMemory - 共享记忆

用于多 Agent 协作：

```python
from src.agent import SharedMemory

shared = SharedMemory()

# Agent A 存储数据
shared.set("user_preference", "dark_mode")
shared.set("session_id", "abc123", metadata={"created_by": "agent_a"})

# Agent B 读取数据
preference = shared.get("user_preference")
session = shared.get("session_id")

# 检查键是否存在
if shared.has("session_id"):
    print("Session active")

# 获取所有键
keys = shared.keys()

# 导出所有数据
data = shared.to_dict()
```

### 4. Executor (执行器)

AgentExecutor 管理 Agent 的执行循环：

```python
from src.agent import AgentExecutor

executor = AgentExecutor(
    agent=agent,
    tool_registry=registry,
    memory=memory,
    verbose=True  # 打印详细日志
)

# 同步执行
result = executor.run("User input here")

# 异步执行
result = await executor.arun("User input here")

# 重置记忆
executor.reset_memory()
```

## Agent 类型

### 1. Tools Agent (基于工具的代理)

最常用的类型，Agent 自主选择和使用工具：

```python
config = AgentConfig(
    name="assistant",
    agent_type=AgentType.TOOLS,
    tools=["search", "calculator", "email", "weather"]
)
```

**使用场景**：
- 通用助手
- 任务自动化
- 信息检索和处理

### 2. Conversational Agent (对话型代理)

纯对话，不使用工具：

```python
config = AgentConfig(
    name="chatbot",
    agent_type=AgentType.CONVERSATIONAL,
    tools=[]  # 无工具
)
```

**使用场景**：
- 聊天机器人
- 客服对话
- 教育辅导

### 3. Router Agent (路由代理)

根据条件将请求路由到不同的处理流程：

```python
from src.agent import WorkflowNode, NodeType

router_node = WorkflowNode(
    id="router",
    type=NodeType.CONDITION,
    name="Route Request",
    condition=lambda results, mem: classify_request(results),
    next_nodes=["path_a", "path_b"]
)
```

**使用场景**：
- 请求分类
- 工作流分支
- 动态路由

### 4. Hierarchical Agent (分层代理)

主 Agent 管理多个子 Agent：

```python
# 创建专业子 Agent
researcher = Agent(config=researcher_config, client=client)
analyst = Agent(config=analyst_config, client=client)
writer = Agent(config=writer_config, client=client)

# 主 Agent 协调
agents = {
    "researcher": researcher,
    "analyst": analyst,
    "writer": writer
}

workflow = Workflow(config=workflow_config, agents=agents)
```

**使用场景**：
- 复杂任务分解
- 专业化分工
- 团队协作模拟

## 工具系统

### 内置工具

#### 1. Calculator (计算器)

```python
from src.agent.builtin_tools import create_calculator_tool

registry.register(create_calculator_tool())

# 支持的操作：
# - 基本运算: +, -, *, /
# - 函数: sqrt, sin, cos, tan
# - 常量: pi, e
```

#### 2. String Tools (字符串工具)

```python
from src.agent.builtin_tools import create_string_tools

for tool in create_string_tools():
    registry.register(tool)

# 可用工具：
# - to_uppercase: 转大写
# - to_lowercase: 转小写
# - reverse_string: 反转字符串
# - count_words: 统计词数
```

#### 3. Data Formatter (数据格式化)

```python
from src.agent.builtin_tools import create_data_formatter_tool

registry.register(create_data_formatter_tool())

# 支持格式：
# - JSON (格式化)
# - YAML
# - Table (表格)
```

### 创建自定义工具

#### 简单工具

```python
def get_current_time() -> ToolResult:
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return ToolResult(success=True, output=now)

registry.register_function(
    name="get_time",
    description="Get current date and time",
    function=get_current_time
)
```

#### 带参数的工具

```python
def send_email(to: str, subject: str, body: str) -> ToolResult:
    # 发送邮件逻辑
    try:
        # send_email_api(to, subject, body)
        return ToolResult(
            success=True,
            output=f"Email sent to {to}",
            metadata={"to": to, "subject": subject}
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))

registry.register_function(
    name="send_email",
    description="Send an email",
    function=send_email
)
```

#### 异步工具

```python
async def async_search(query: str) -> ToolResult:
    # 异步搜索
    results = await search_api(query)
    return ToolResult(success=True, output=results)

tool = Tool(
    name="async_search",
    description="Search asynchronously",
    function=None,
    async_function=async_search,
    parameters={...}
)
```

## 工作流编排

### 创建工作流

```python
from src.agent import Workflow, WorkflowConfig, WorkflowNode, NodeType

# 1. 定义节点
nodes = [
    WorkflowNode(
        id="research",
        type=NodeType.AGENT,
        name="Research",
        agent_name="researcher",
        next_nodes=["analyze"]
    ),
    WorkflowNode(
        id="analyze",
        type=NodeType.AGENT,
        name="Analyze",
        agent_name="analyst",
        next_nodes=["write"]
    ),
    WorkflowNode(
        id="write",
        type=NodeType.AGENT,
        name="Write",
        agent_name="writer",
        next_nodes=[]
    )
]

# 2. 创建工作流配置
config = WorkflowConfig(
    name="research_pipeline",
    description="Research -> Analyze -> Write",
    start_node="research",
    nodes=nodes,
    max_iterations=20,
    enable_shared_memory=True
)

# 3. 创建工作流
workflow = Workflow(
    config=config,
    agents={
        "researcher": researcher_agent,
        "analyst": analyst_agent,
        "writer": writer_agent
    },
    tool_registry=registry,
    shared_memory=SharedMemory()
)

# 4. 运行工作流
result = workflow.run("Research quantum computing")
```

### 节点类型

#### 1. AGENT 节点

执行一个 Agent：

```python
WorkflowNode(
    id="node1",
    type=NodeType.AGENT,
    name="Process Data",
    agent_name="processor",
    next_nodes=["node2"]
)
```

#### 2. CONDITION 节点

条件分支：

```python
def check_quality(results, shared_memory):
    score = results.get("quality_score", 0)
    return score > 0.8

WorkflowNode(
    id="quality_check",
    type=NodeType.CONDITION,
    name="Check Quality",
    condition=check_quality,
    next_nodes=["high_quality_path", "low_quality_path"]
)
```

#### 3. HUMAN_IN_LOOP 节点

人工干预：

```python
def get_human_input(prompt):
    return input(prompt)

workflow = Workflow(
    config=config,
    agents=agents,
    human_input_handler=get_human_input
)

WorkflowNode(
    id="approval",
    type=NodeType.HUMAN_IN_LOOP,
    name="Human Approval"
)
```

## 高级用法

### 1. 异步执行

```python
import asyncio

async def main():
    # 异步 Agent 执行
    result = await executor.arun("User input")

    # 异步工作流
    workflow_result = await workflow.arun("Task input")

    print(result.output)

asyncio.run(main())
```

### 2. 并发工具调用

Agent 会自动并发调用多个工具（如果 LLM 返回多个工具调用）。

### 3. 错误处理

```python
result = executor.run("User input")

if result.success:
    print(f"Success: {result.output}")
else:
    print(f"Error: {result.error}")
    print(f"Completed iterations: {result.iterations}")
    print(f"Tool calls: {result.tool_calls}")
```

### 4. 自定义提供商适配

```python
# 工具会自动转换为提供商特定格式
tools_openai = registry.get_tools_for_provider("openai")
tools_anthropic = registry.get_tools_for_provider("anthropic")
```

## 最佳实践

### 1. 工具设计

✅ **好的做法**：
- 工具名称清晰描述功能
- 参数描述详细具体
- 返回结构化数据
- 处理错误并返回 ToolResult

❌ **避免**：
- 工具功能过于复杂
- 参数名称模糊
- 直接抛出异常

```python
# 好的示例
def search_products(category: str, max_results: int = 10) -> ToolResult:
    """Search for products in a specific category."""
    try:
        results = api.search(category=category, limit=max_results)
        return ToolResult(
            success=True,
            output=results,
            metadata={"category": category, "count": len(results)}
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))
```

### 2. Prompt 设计

✅ **好的系统提示词**：
```python
system_prompt = """You are a research assistant specialized in scientific papers.

Your capabilities:
- Search academic databases
- Summarize papers
- Extract key findings
- Compare multiple sources

When using tools:
1. Always verify the information
2. Cite your sources
3. Be concise but thorough

Remember: Quality over quantity."""
```

### 3. 记忆管理

- 为短对话使用小窗口（5-10 条消息）
- 为长对话使用大窗口（20-50 条消息）
- 定期清理不需要的记忆
- 使用 SharedMemory 在 Agent 间共享关键信息

### 4. 工作流设计

- 将复杂任务分解为简单步骤
- 每个 Agent 专注于单一职责
- 使用条件节点处理不同场景
- 在关键点添加人工审核

### 5. 调试和监控

```python
# 启用详细日志
executor = AgentExecutor(agent=agent, tool_registry=registry, verbose=True)

# 检查执行结果
result = executor.run("Task")
print(f"Iterations: {result.iterations}")
print(f"Tool calls: {len(result.tool_calls)}")
for call in result.tool_calls:
    print(f"  Tool: {call['tool']}")
    print(f"  Args: {call['arguments']}")
    print(f"  Result: {call['result']}")
```

## 示例场景

### 场景 1: 数据分析助手

```python
# 创建数据分析工具
tools = [
    create_calculator_tool(),
    create_data_formatter_tool(),
    create_custom_plot_tool()
]

config = AgentConfig(
    name="data_analyst",
    model="gpt-4",
    provider="openai",
    system_prompt="You are a data analyst. Analyze data and create visualizations.",
    tools=["calculator", "format_data", "create_plot"]
)
```

### 场景 2: 内容创作流水线

```python
# 研究 -> 大纲 -> 撰写 -> 审核
workflow_config = WorkflowConfig(
    name="content_pipeline",
    start_node="research",
    nodes=[
        WorkflowNode(id="research", type=NodeType.AGENT, agent_name="researcher", next_nodes=["outline"]),
        WorkflowNode(id="outline", type=NodeType.AGENT, agent_name="outliner", next_nodes=["write"]),
        WorkflowNode(id="write", type=NodeType.AGENT, agent_name="writer", next_nodes=["review"]),
        WorkflowNode(id="review", type=NodeType.AGENT, agent_name="reviewer", next_nodes=[])
    ]
)
```

### 场景 3: 客户服务自动化

```python
# 路由客户请求
def classify_request(results, mem):
    intent = results.get("intent", "")
    return intent in ["technical", "billing"]

nodes = [
    WorkflowNode(id="classify", type=NodeType.AGENT, agent_name="classifier", next_nodes=["route"]),
    WorkflowNode(id="route", type=NodeType.CONDITION, condition=classify_request, next_nodes=["technical", "billing"]),
    WorkflowNode(id="technical", type=NodeType.AGENT, agent_name="tech_support", next_nodes=[]),
    WorkflowNode(id="billing", type=NodeType.AGENT, agent_name="billing_support", next_nodes=[])
]
```

## 资源和参考

- [n8n Documentation](https://docs.n8n.io/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic Tool Use](https://docs.anthropic.com/claude/docs/tool-use)
- 查看 `examples/` 目录获取更多代码示例

## 常见问题

### Q: Agent 达到最大迭代次数怎么办？

A: 增加 `max_iterations` 或优化工具和提示词，使 Agent 更高效。

### Q: 如何处理工具调用失败？

A: ToolResult 包含错误信息，Agent 会看到错误并可以重试或采取其他行动。

### Q: 可以使用哪些 LLM 提供商？

A: 所有 UnifyLLM 支持的提供商都可以用于 Agent（OpenAI、Anthropic、Gemini、Ollama 等）。

### Q: 工作流可以有循环吗？

A: 可以，但要小心避免无限循环。使用 `max_iterations` 限制。

### Q: 如何在 Agent 间共享数据？

A: 使用 SharedMemory 在多个 Agent 间共享状态和数据。
