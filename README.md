# UnifyLLM

**统一的大语言模型接口调用框架**

UnifyLLM 是一个 Python 框架，提供统一的接口来调用各种大语言模型 API。通过 UnifyLLM，您可以使用相同的代码调用 OpenAI、Anthropic、Google Gemini、Ollama 等不同的 LLM 提供商。

## 核心特性

### LLM 调用
- ✅ **统一接口**: 所有 LLM 提供商使用相同的调用方式
- ✅ **多提供商支持**: OpenAI, Anthropic (Claude), Google Gemini, Ollama, Databricks
- ✅ **流式/非流式**: 支持两种响应模式
- ✅ **同步/异步**: 完整支持同步和异步调用
- ✅ **错误处理**: 统一的异常类型和自动重试机制
- ✅ **类型提示**: 完整的 Python type hints

### AI Agent 框架 (🆕 New!)
- 🤖 **智能代理**: 支持工具调用的自主 AI 代理
- 🔧 **工具系统**: 灵活的工具注册和执行机制
- 🧠 **记忆管理**: 对话历史和共享内存支持
- 🔄 **工作流编排**: 多代理协作和工作流自动化
- 📊 **多种模式**: 支持顺序、并行、条件分支等执行模式
- 🎯 **类似 n8n**: 借鉴 n8n 的设计理念，提供强大的自动化能力

### MCP & A2A 协议 (🔥 Latest!)
- 🌐 **MCP (Model Context Protocol)**: Anthropic 的开放协议，暴露工具、资源和提示
- 🤝 **A2A (Agent-to-Agent)**: 多代理通信和协作协议
- 🔍 **代理发现**: 自动发现和连接具有特定能力的代理
- 📡 **任务委托**: 智能任务分配和执行
- 🗳️ **共识机制**: 多代理投票和决策
- 🚀 **Databricks 支持**: 完整支持 Claude Opus 4.5 测试

## 安装

```bash
pip install unify-llm
```

或从源码安装：

```bash
git clone https://github.com/yourusername/unify-llm.git
cd unify-llm
pip install -e .
```

## 快速开始

### 基本用法

```python
from src import UnifyLLM

# 初始化客户端
client = UnifyLLM(
    provider="openai",
    api_key="your-api-key"
)

# 发送消息
response = client.chat(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "Hello, how are you?"}
    ]
)

print(response.content)
```

### 流式响应

```python
for chunk in client.chat_stream(
    model="gpt-4",
    messages=[{"role": "user", "content": "Tell me a story"}]
):
    print(chunk.content, end="", flush=True)
```

### 异步调用

```python
import asyncio

async def main():
    response = await client.achat(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print(response.content)

asyncio.run(main())
```

## 支持的提供商

### OpenAI

```python
client = UnifyLLM(
    provider="openai",
    api_key="sk-..."
)

response = client.chat(
    model="gpt-4",  # 或 "gpt-3.5-turbo"
    messages=[{"role": "user", "content": "Hello"}]
)
```

**支持的模型**: `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`, 等

### Anthropic (Claude)

```python
client = UnifyLLM(
    provider="anthropic",
    api_key="sk-ant-..."
)

response = client.chat(
    model="claude-3-opus-20240229",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=1000  # Anthropic 要求设置 max_tokens
)
```

**支持的模型**: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`, 等

### Google Gemini

```python
client = UnifyLLM(
    provider="gemini",
    api_key="your-gemini-api-key"
)

response = client.chat(
    model="gemini-pro",
    messages=[{"role": "user", "content": "Hello"}]
)
```

**支持的模型**: `gemini-pro`, `gemini-pro-vision`, 等

### Ollama (本地模型)

```python
client = UnifyLLM(
    provider="ollama",
    base_url="http://localhost:11434"  # 默认值
)

response = client.chat(
    model="llama2",  # 或其他已安装的模型
    messages=[{"role": "user", "content": "Hello"}]
)
```

**支持的模型**: 任何通过 Ollama 安装的模型 (llama2, mistral, phi, 等)

### Databricks

Databricks 提供 OpenAI 兼容的 API 端点，用于部署和调用模型。

```python
# 方式1: 自动从环境变量读取 (推荐)
client = UnifyLLM(provider="databricks")

# 方式2: 手动指定
client = UnifyLLM(
    provider="databricks",
    api_key="dapi...",
    base_url="https://your-workspace.cloud.databricks.com/serving-endpoints"
)

response = client.chat(
    model="your-endpoint-name",  # Databricks serving endpoint 名称
    messages=[{"role": "user", "content": "Hello"}]
)
```

**环境变量配置**:
- `DATABRICKS_API_KEY`: Databricks 个人访问令牌
- `DATABRICKS_BASE_URL`: Databricks serving endpoint 的基础 URL

**支持的模型**: 任何在 Databricks 上部署的模型 (DBRX, Llama, Mixtral, 等)

## API 文档

### UnifyLLM 类

#### 初始化参数

- `provider` (str): 提供商名称 ("openai", "anthropic", "gemini", "ollama", "databricks")
- `api_key` (str, optional): API 密钥
- `base_url` (str, optional): 自定义 API 端点
- `timeout` (float, optional): 请求超时时间（秒），默认 60
- `max_retries` (int, optional): 最大重试次数，默认 3
- `organization` (str, optional): 组织 ID（仅部分提供商支持）
- `extra_headers` (dict, optional): 额外的 HTTP 请求头

#### chat() 方法

同步聊天请求。

```python
response = client.chat(
    model: str,                          # 模型名称
    messages: List[Dict],                # 消息列表
    temperature: float = None,           # 温度参数 (0.0-2.0)
    max_tokens: int = None,              # 最大生成 token 数
    top_p: float = None,                 # Top-p 采样
    frequency_penalty: float = None,     # 频率惩罚
    presence_penalty: float = None,      # 存在惩罚
    stop: Union[str, List[str]] = None,  # 停止序列
    **extra_params                       # 提供商特定参数
)
```

**返回**: `ChatResponse` 对象

#### chat_stream() 方法

同步流式聊天请求。

```python
for chunk in client.chat_stream(
    model: str,
    messages: List[Dict],
    **params  # 同 chat() 方法
):
    print(chunk.content, end="")
```

**返回**: `Iterator[StreamChunk]`

#### achat() 方法

异步聊天请求（参数同 `chat()`）。

```python
response = await client.achat(...)
```

**返回**: `ChatResponse` 对象

#### achat_stream() 方法

异步流式聊天请求（参数同 `chat()`）。

```python
async for chunk in client.achat_stream(...):
    print(chunk.content, end="")
```

**返回**: `AsyncIterator[StreamChunk]`

### 数据模型

#### Message

```python
class Message:
    role: str                           # "system", "user", "assistant"
    content: str                        # 消息内容
    name: Optional[str] = None          # 发送者名称
```

#### ChatResponse

```python
class ChatResponse:
    id: str                             # 响应 ID
    model: str                          # 使用的模型
    choices: List[ChatResponseChoice]   # 生成的选项
    usage: Usage                        # Token 使用情况
    created: int                        # 创建时间戳
    provider: str                       # 提供商名称

    # 便捷属性
    @property
    def content(self) -> str:           # 第一个选项的内容
        ...

    @property
    def finish_reason(self) -> str:     # 完成原因
        ...
```

#### StreamChunk

```python
class StreamChunk:
    id: str                             # 流 ID
    model: str                          # 使用的模型
    choices: List[StreamChoiceDelta]    # 增量更新
    created: int                        # 创建时间戳
    provider: str                       # 提供商名称

    # 便捷属性
    @property
    def content(self) -> str:           # 内容增量
        ...

    @property
    def finish_reason(self) -> str:     # 完成原因
        ...
```

#### Usage

```python
class Usage:
    prompt_tokens: int                  # 提示词 token 数
    completion_tokens: int              # 生成 token 数
    total_tokens: int                   # 总 token 数
```

### 异常类型

所有异常都继承自 `UnifyLLMError`。

- `AuthenticationError`: 认证失败
- `RateLimitError`: 速率限制
- `InvalidRequestError`: 无效请求
- `APIError`: API 错误
- `TimeoutError`: 请求超时
- `ModelNotFoundError`: 模型未找到
- `ContentFilterError`: 内容被过滤

```python
from src import UnifyLLM, AuthenticationError

try:
    response = client.chat(...)
except AuthenticationError as e:
    print(f"认证失败: {e}")
```

## 高级用法

### 环境变量配置

UnifyLLM 支持从环境变量读取 API 密钥：

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="..."
```

```python
# API 密钥会自动从环境变量读取
client = UnifyLLM(provider="openai")
```

### 自定义提供商

您可以注册自定义提供商：

```python
from src import UnifyLLM
from src.providers import BaseProvider


class MyCustomProvider(BaseProvider):
    # 实现必要的抽象方法
    def _get_headers(self):
        ...

    def _convert_request(self, request):
        ...

    # ... 其他方法 ...


# 注册自定义提供商
UnifyLLM.register_provider("custom", MyCustomProvider)

# 使用自定义提供商
client = UnifyLLM(provider="custom", api_key="...")
```

### 并发请求

```python
import asyncio

async def concurrent_requests():
    client = UnifyLLM(provider="openai", api_key="...")

    tasks = [
        client.achat(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Tell me about {topic}"}]
        )
        for topic in ["Python", "JavaScript", "Rust"]
    ]

    responses = await asyncio.gather(*tasks)

    for response in responses:
        print(response.content)

asyncio.run(concurrent_requests())
```

### 自定义超时和重试

```python
client = UnifyLLM(
    provider="openai",
    api_key="...",
    timeout=120.0,      # 120 秒超时
    max_retries=5       # 最多重试 5 次
)
```

## 示例项目

查看 `examples/` 目录获取更多示例：

- `basic_usage.py`: 基本使用示例
- `streaming.py`: 流式响应示例
- `async_usage.py`: 异步调用示例
- `multi_provider.py`: 多提供商对比示例

## 开发

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
black src tests
ruff check src tests
```

### 类型检查

```bash
mypy src
```

## AI Agent 功能 (🆕 New!)

UnifyLLM 现在支持强大的 AI Agent 功能，灵感来自 n8n 的工作流自动化设计！

### 快速开始：创建一个简单的 Agent

```python
from src import UnifyLLM
from src.agent import Agent, AgentConfig, AgentExecutor, ToolRegistry
from src.agent.builtin_tools import create_calculator_tool

# 初始化客户端
client = UnifyLLM(provider="openai", api_key="sk-...")

# 创建工具注册表
registry = ToolRegistry()
registry.register(create_calculator_tool())

# 配置 Agent
config = AgentConfig(
    name="math_assistant",
    model="gpt-4",
    provider="openai",
    system_prompt="You are a helpful math assistant.",
    tools=["calculator"]
)

# 创建并运行 Agent
agent = Agent(config=config, client=client)
executor = AgentExecutor(agent=agent, tool_registry=registry)

result = executor.run("What is 15 * 23 + 100?")
print(result.output)
```

### 核心组件

#### 1. Agent (智能代理)
- 支持工具选择和调用
- 对话记忆管理
- 多种代理类型（工具型、对话型、路由型、分层型）

#### 2. Tools (工具系统)
- 灵活的工具定义
- 自动参数检测
- 支持同步和异步执行
- 内置工具：计算器、字符串处理、数据格式化等

```python
from src.agent import Tool, ToolParameter, ToolParameterType, ToolResult


def my_custom_tool(param1: str, param2: int) -> ToolResult:
    # 自定义逻辑
    result = f"Processing {param1} with {param2}"
    return ToolResult(success=True, output=result)


# 注册工具
registry.register_function(
    name="my_tool",
    description="My custom tool",
    function=my_custom_tool
)
```

#### 3. Memory (记忆系统)
- **ConversationMemory**: 对话历史管理
- **SharedMemory**: 多代理共享内存

```python
from src.agent import ConversationMemory

memory = ConversationMemory(window_size=10)
memory.add_user_message("Hello!")
memory.add_assistant_message("Hi! How can I help?")
```

#### 4. Workflow (工作流编排)
支持多代理协作的复杂工作流：

```python
from src.agent import Workflow, WorkflowConfig, WorkflowNode, NodeType

# 定义工作流：研究 -> 分析 -> 撰写
workflow_config = WorkflowConfig(
    name="research_workflow",
    description="Research, analyze, and write",
    start_node="research",
    nodes=[
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
)

# 创建并运行工作流
workflow = Workflow(
    config=workflow_config,
    agents={"researcher": researcher, "analyst": analyst, "writer": writer}
)

result = workflow.run("Explain quantum computing")
```

### Agent 架构模式

#### 1. Tools-Based Agent (基于工具的代理)
代理自主选择和使用工具：
```python
config = AgentConfig(
    name="assistant",
    agent_type=AgentType.TOOLS,
    tools=["search", "calculator", "email"]
)
```

#### 2. Router Agent (路由代理)
根据条件分发任务：
```python
WorkflowNode(
    id="router",
    type=NodeType.CONDITION,
    condition=lambda results, mem: check_condition(results)
)
```

#### 3. Hierarchical Agent (分层代理)
主代理管理多个子代理：
```python
# 主代理协调多个专业代理
agents = {
    "manager": manager_agent,
    "researcher": research_agent,
    "writer": writer_agent,
    "reviewer": review_agent
}
```

#### 4. Human-in-the-Loop (人机协作)
在关键节点需要人工干预：
```python
WorkflowNode(
    id="approval",
    type=NodeType.HUMAN_IN_LOOP,
    name="Human Approval"
)
```

### 内置工具

UnifyLLM 提供了多种开箱即用的工具：

**基础工具**:
- **calculator**: 数学计算（支持基本运算和函数）
- **to_uppercase/to_lowercase**: 字符串大小写转换
- **reverse_string**: 字符串反转
- **count_words**: 词数统计
- **format_data**: 数据格式化（JSON、YAML、表格）

**扩展工具**:
- **日期时间工具**: get_current_datetime, calculate_date_diff, add_time_to_date
- **文本分析工具**: extract_emails, extract_urls, extract_numbers, analyze_text_stats
- **文件操作工具**: read_text_file, write_text_file, list_directory
- **JSON 工具**: parse_json, stringify_json, extract_json_field

### Agent 模板

使用预配置的 Agent 模板快速开始：

```python
from src.agent import AgentTemplates, Agent

# 研究助手
config = AgentTemplates.research_assistant()

# 代码助手
config = AgentTemplates.code_assistant()

# 数据分析师
config = AgentTemplates.data_analyst()

# 内容作家
config = AgentTemplates.content_writer()

# 客服代表
config = AgentTemplates.customer_support()

# 任务规划师
config = AgentTemplates.task_planner()
```

### 高级功能

#### 1. 并行执行

```python
from src.agent import ParallelExecutor

parallel = ParallelExecutor(max_workers=3)
results = parallel.execute_parallel(
    agents=[agent1, agent2, agent3],
    executors=[exec1, exec2, exec3],
    inputs=["task 1", "task 2", "task 3"]
)
```

#### 2. 错误处理和重试

```python
from src.agent import ErrorHandler

handler = ErrorHandler(max_retries=3, backoff_factor=2.0)
result = handler.execute_with_retry(
    executor=executor,
    user_input="task",
    on_error=lambda e: print(f"Error: {e}")
)
```

#### 3. Agent 链式调用

```python
from src.agent import AgentChain

chain = AgentChain()
chain.add_agent(researcher, researcher_exec)
chain.add_agent(analyst, analyst_exec, transform=lambda x: f"Analyze: {x}")
chain.add_agent(writer, writer_exec, transform=lambda x: f"Write about: {x}")

result = chain.execute("Research AI trends")
```

#### 4. 工作流可视化

```python
from src.agent import WorkflowVisualizer

viz = WorkflowVisualizer(workflow)

# ASCII 图
print(viz.to_ascii())

# Mermaid 图（可在 GitHub/Markdown 中渲染）
print(viz.to_mermaid())

# JSON 导出
print(viz.to_json())
```

#### 5. 性能监控

```python
from src.agent import PerformanceMonitor

monitor = PerformanceMonitor()

# 跟踪执行
with monitor.track("my_agent"):
    result = executor.run("task")

# 记录结果
monitor.record_result("my_agent", result)

# 查看指标
monitor.print_summary()
```

### 完整示例

查看 `examples/` 目录获取更多示例：

- `agent_basic.py`: 基础 Agent 使用
- `agent_workflow.py`: 多代理工作流
- `agent_custom_tools.py`: 自定义工具
- `agent_advanced.py`: 高级功能（并行、错误处理、链式调用）

## MCP & A2A 协议功能 (🔥 Latest!)

UnifyLLM 现在支持 MCP (Model Context Protocol) 和 A2A (Agent-to-Agent) 协议！

### MCP Protocol - 暴露代理能力

使用 MCP 将代理的工具、资源和提示暴露为标准化服务：

```python
from src.mcp import MCPServer, MCPServerConfig

# 创建 MCP 服务器
server = MCPServer(MCPServerConfig(server_name="my-agent"))


# 注册工具
@server.tool("calculator", "执行数学计算")
async def calculator(expression: str) -> dict:
    return {"result": eval(expression)}


# 注册资源
@server.resource("file://data.json", "application/json", "数据资源")
async def get_data() -> str:
    return '{"data": "value"}'


# 注册提示模板
@server.prompt("greeting", "生成问候语")
async def greeting_prompt(name: str) -> dict:
    return {
        "messages": [
            {"role": "user", "content": f"Say hello to {name}"}
        ]
    }
```

### A2A Protocol - 代理间通信

使用 A2A 协议让多个代理相互通信和协作：

```python
from src import UnifyLLM
from src.agent import Agent, AgentConfig
from src.a2a import A2AAgent, A2AAgentConfig, AgentCapability, AgentRegistry

# 创建共享注册表
registry = AgentRegistry()

# 创建 A2A 代理
client = UnifyLLM(provider="databricks", api_key="...", base_url="...")
base_agent = Agent(
    config=AgentConfig(name="math_expert", model="claude-opus-4-5", provider="databricks"),
    client=client
)

a2a_agent = A2AAgent(
    base_agent=base_agent,
    config=A2AAgentConfig(
        agent_name="math_expert",
        capabilities=[
            AgentCapability(
                name="solve_math",
                description="解决数学问题",
                input_schema={"type": "object", "properties": {"problem": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"solution": {"type": "string"}}}
            )
        ]
    ),
    registry=registry
)

await a2a_agent.start()

# 发现其他代理
from src.a2a import AgentDiscovery

discovery = AgentDiscovery(registry)
agents = await discovery.discover(capabilities=["solve_math"])

# 委托任务
result = await a2a_agent.delegate_task(
    target_agent_id=other_agent.agent_id,
    capability="solve_math",
    input_data={"problem": "What is 15 * 23?"}
)
```

### 多代理协作

使用不同策略进行多代理协作：

```python
from src.a2a import AgentCollaboration, CollaborationStrategy

# 顺序协作 (sequential)
collab = AgentCollaboration(strategy=CollaborationStrategy.SEQUENTIAL)
collab.add_agent(researcher)
collab.add_agent(analyst)
collab.add_agent(writer)
result = await collab.execute({"task": "create_report", "data": {...}})

# 并行协作 (parallel)
collab = AgentCollaboration(strategy=CollaborationStrategy.PARALLEL)
collab.add_agent(agent1)
collab.add_agent(agent2)
result = await collab.execute({"task": "parallel_analysis", "data": {...}})

# 共识协作 (consensus)
collab = AgentCollaboration(strategy=CollaborationStrategy.CONSENSUS)
collab.add_agent(expert1)
collab.add_agent(expert2)
collab.add_agent(expert3)
result = await collab.execute({
    "task": "make_decision",
    "data": {"question": "Should we proceed?"},
    "voting_method": "majority"
})
```

### 使用 Databricks Claude Opus 4.5 测试

```bash
# 设置环境变量
export DATABRICKS_API_KEY="dapi..."
export DATABRICKS_BASE_URL="https://your-workspace.cloud.databricks.com"

# 运行测试
python tests/test_mcp_a2a_databricks.py
```

查看完整文档：
- [MCP & A2A 完整指南](docs/MCP_A2A_GUIDE.md)
- [Databricks 代理测试](docs/DATABRICKS_AGENT_GUIDE.md)

## 项目定位

UnifyLLM 现在提供：

✅ **统一的 LLM API 调用接口**
✅ **AI Agent 框架**（工具调用、记忆管理、工作流编排）
✅ **多代理协作**
✅ **MCP Protocol** (Model Context Protocol) - 标准化工具暴露
✅ **A2A Protocol** (Agent-to-Agent) - 代理间通信和协作
✅ **Databricks 支持** - Claude Opus 4.5 完整集成

**不涉及**：
- ❌ 向量数据库
- ❌ 文档加载器
- ❌ RAG 特定实现（但提供构建 RAG 的基础）

如果您需要更高级的 RAG 功能或向量数据库集成，可以考虑与 LangChain 或 LlamaIndex 结合使用。

## 路线图

- [x] 支持 MCP (Model Context Protocol)
- [x] 支持 A2A (Agent-to-Agent Protocol)
- [x] Databricks Claude Opus 4.5 集成
- [ ] 支持更多国内模型（智谱、文心、通义千问等）
- [ ] 支持 vLLM
- [ ] 函数调用（Function Calling）支持优化
- [ ] 批量请求优化
- [ ] 更详细的使用文档
- [ ] 性能基准测试
- [ ] MCP 服务器注册中心
- [ ] A2A 消息总线实现

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 致谢

UnifyLLM 受到以下项目的启发：

- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [LiteLLM](https://github.com/BerriAI/litellm)
- [LangChain](https://github.com/langchain-ai/langchain)

---

**Star 这个项目** 如果您觉得它有用！
