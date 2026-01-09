# AI Agent Quick Reference

## 基本用法

### 创建简单 Agent

```python
from src import UnifyLLM, Agent, AgentConfig, AgentExecutor, ToolRegistry
from src.agent.builtin_tools import create_calculator_tool

client = UnifyLLM(provider="openai", api_key="...")
registry = ToolRegistry()
registry.register(create_calculator_tool())

config = AgentConfig(
    name="assistant",
    model="gpt-4",
    provider="openai",
    tools=["calculator"]
)

agent = Agent(config=config, client=client)
executor = AgentExecutor(agent=agent, tool_registry=registry)
result = executor.run("What is 15 * 23?")
```

### 创建自定义工具

```python
from src.agent import Tool, ToolParameter, ToolParameterType, ToolResult


def my_tool(param: str) -> ToolResult:
    return ToolResult(success=True, output=f"Result: {param}")


registry.register_function(
    name="my_tool",
    description="My custom tool",
    function=my_tool
)
```

### 创建工作流

```python
from src.agent import Workflow, WorkflowConfig, WorkflowNode, NodeType

config = WorkflowConfig(
    name="my_workflow",
    start_node="step1",
    nodes=[
        WorkflowNode(id="step1", type=NodeType.AGENT, agent_name="agent1", next_nodes=["step2"]),
        WorkflowNode(id="step2", type=NodeType.AGENT, agent_name="agent2", next_nodes=[])
    ]
)

workflow = Workflow(config=config, agents={"agent1": agent1, "agent2": agent2})
result = workflow.run("Task input")
```

## API 参考

### AgentConfig

```python
AgentConfig(
    name: str,                    # Agent 名称
    agent_type: AgentType,        # Agent 类型 (TOOLS, CONVERSATIONAL, ROUTER, HIERARCHICAL)
    model: str,                   # 模型名称
    provider: str,                # 提供商名称
    system_prompt: str,           # 系统提示词
    temperature: float = 0.7,     # 温度
    max_tokens: int = None,       # 最大 tokens
    max_iterations: int = 10,     # 最大迭代次数
    enable_memory: bool = True,   # 启用记忆
    memory_window: int = 10,      # 记忆窗口大小
    tools: List[str] = [],        # 工具名称列表
    metadata: Dict = {}           # 元数据
)
```

### Tool

```python
Tool(
    name: str,                         # 工具名称
    description: str,                  # 工具描述
    parameters: Dict[str, ToolParameter],  # 参数定义
    function: Callable,                # 同步函数
    async_function: Callable = None    # 异步函数
)
```

### ToolParameter

```python
ToolParameter(
    type: ToolParameterType,       # 参数类型 (STRING, NUMBER, INTEGER, BOOLEAN, OBJECT, ARRAY)
    description: str,              # 参数描述
    required: bool = True,         # 是否必需
    enum: List = None,             # 枚举值
    default: Any = None            # 默认值
)
```

### WorkflowNode

```python
WorkflowNode(
    id: str,                       # 节点 ID
    type: NodeType,                # 节点类型 (AGENT, CONDITION, PARALLEL, SEQUENTIAL, HUMAN_IN_LOOP)
    name: str,                     # 节点名称
    agent_name: str = None,        # Agent 名称 (AGENT 类型)
    condition: Callable = None,    # 条件函数 (CONDITION 类型)
    next_nodes: List[str] = [],    # 下一个节点列表
    metadata: Dict = {}            # 元数据
)
```

## 内置工具

| 工具名称 | 描述 | 参数 |
|---------|------|------|
| `calculator` | 数学计算 | `expression: str` |
| `to_uppercase` | 转大写 | `text: str` |
| `to_lowercase` | 转小写 | `text: str` |
| `reverse_string` | 反转字符串 | `text: str` |
| `count_words` | 统计词数 | `text: str` |
| `format_data` | 格式化数据 | `data: str`, `format_type: str` |

## 常用模式

### 模式 1: 简单任务自动化

```python
# 使用单个 Agent + 工具
executor = AgentExecutor(agent=agent, tool_registry=registry)
result = executor.run("Execute task")
```

### 模式 2: 多步骤流水线

```python
# 顺序执行多个 Agent
workflow = Workflow(config=sequential_config, agents=agents)
result = workflow.run("Start task")
```

### 模式 3: 条件分支

```python
# 根据条件选择不同路径
WorkflowNode(
    id="router",
    type=NodeType.CONDITION,
    condition=lambda r, m: r.get("score") > 0.8,
    next_nodes=["high_score", "low_score"]
)
```

### 模式 4: 人工干预

```python
# 在关键步骤需要人工确认
WorkflowNode(
    id="approval",
    type=NodeType.HUMAN_IN_LOOP,
    name="Approval Required"
)
```

## 错误处理

```python
result = executor.run("Task")

if result.success:
    print(f"✓ Success: {result.output}")
else:
    print(f"✗ Error: {result.error}")
    print(f"Iterations: {result.iterations}")
    for call in result.tool_calls:
        print(f"Tool: {call['tool']}, Success: {call['result']['success']}")
```

## 调试技巧

```python
# 1. 启用详细日志
executor = AgentExecutor(agent=agent, tool_registry=registry, verbose=True)

# 2. 检查工具调用
result = executor.run("Task")
print(f"Tool calls: {len(result.tool_calls)}")
for call in result.tool_calls:
    print(call)

# 3. 检查记忆
messages = executor.memory.get_messages()
print(f"Messages in memory: {len(messages)}")

# 4. 检查共享内存
print(f"Shared data: {workflow.shared_memory.to_dict()}")
```

## 性能优化

1. **限制迭代次数**: 设置合理的 `max_iterations`
2. **优化记忆窗口**: 使用适当的 `memory_window` 大小
3. **精简工具**: 只注册必要的工具
4. **优化提示词**: 清晰的指令减少迭代
5. **使用异步**: 对于 I/O 密集任务使用 `arun()`

## 相关资源

- 完整文档: `docs/AI_AGENT_GUIDE.md`
- 示例代码: `examples/agent_*.py`
- n8n 参考: https://docs.n8n.io/
