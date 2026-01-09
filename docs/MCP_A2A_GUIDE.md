# MCP and A2A Protocol Guide for UnifyLLM

## 概述

UnifyLLM 现在支持两个强大的协议来增强 AI 代理的能力：

1. **MCP (Model Context Protocol)**: Anthropic 的开放协议，用于连接 AI 助手与外部数据源和工具
2. **A2A (Agent-to-Agent Protocol)**: 实现多个 AI 代理之间的通信和协作

## 目录

- [MCP Protocol](#mcp-protocol)
  - [MCP 服务器](#mcp-服务器)
  - [MCP 客户端](#mcp-客户端)
  - [传输层](#传输层)
- [A2A Protocol](#a2a-protocol)
  - [A2A 代理](#a2a-代理)
  - [代理发现](#代理发现)
  - [任务委托](#任务委托)
  - [多代理协作](#多代理协作)
- [使用 Databricks Claude Opus 4.5 测试](#使用-databricks-claude-opus-45-测试)
- [完整示例](#完整示例)

---

## MCP Protocol

MCP (Model Context Protocol) 允许 AI 代理通过标准化的方式暴露工具、资源和提示模板。

### MCP 服务器

创建 MCP 服务器来暴露代理的能力：

```python
from src.mcp import MCPServer, MCPServerConfig

# 创建服务器
config = MCPServerConfig(
    server_name="my-agent-server",
    server_version="1.0.0"
)
server = MCPServer(config)


# 注册工具
@server.tool("calculator", "Perform mathematical calculations")
async def calculator(expression: str) -> dict:
    result = eval(expression)
    return {"result": result}


# 注册资源
@server.resource("file://data.json", "application/json", "Data resource")
async def get_data() -> str:
    return '{"data": "value"}'


# 注册提示模板
@server.prompt("greeting", "Generate a greeting")
async def greeting_prompt(name: str) -> dict:
    return {
        "messages": [
            {"role": "user", "content": f"Say hello to {name}"}
        ]
    }


# 启动服务器
from src.mcp import StdioTransport

transport = StdioTransport()
await server.start(transport)
```

### MCP 客户端

连接到 MCP 服务器并使用其功能：

```python
from src.mcp import MCPClient, MCPClientConfig, StdioTransport

# 创建客户端
config = MCPClientConfig(client_name="my-app")
transport = StdioTransport()
client = MCPClient(config, transport)

# 连接并初始化
await client.connect()
await client.initialize()

# 列出可用工具
tools = await client.list_tools()
for tool in tools:
    print(f"Tool: {tool.name} - {tool.description}")

# 调用工具
result = await client.call_tool("calculator", {"expression": "2+2"})
print(result)

# 读取资源
resources = await client.list_resources()
content = await client.read_resource(resources[0].uri)

# 获取提示
prompts = await client.list_prompts()
prompt = await client.get_prompt("greeting", {"name": "Alice"})

# 关闭连接
await client.close()
```

### 传输层

MCP 支持多种传输方式：

#### Stdio Transport (进程间通信)

```python
from src.mcp import StdioTransport

transport = StdioTransport()
await transport.connect()
```

#### SSE Transport (Server-Sent Events)

```python
from src.mcp import SSETransport

transport = SSETransport(url="http://localhost:3000/sse")
await transport.connect()
```

#### WebSocket Transport

```python
from src.mcp import WebSocketTransport

transport = WebSocketTransport(url="ws://localhost:3000/ws")
await transport.connect()
```

---

## A2A Protocol

A2A (Agent-to-Agent) Protocol 使多个 AI 代理能够相互通信和协作。

### A2A 代理

将标准代理包装为 A2A 代理：

```python
from src import UnifyLLM
from src.agent import Agent, AgentConfig
from src.a2a import A2AAgent, A2AAgentConfig, AgentCapability

# 创建基础代理
client = UnifyLLM(provider="databricks", api_key="...", base_url="...")
base_agent = Agent(
    config=AgentConfig(
        name="math_expert",
        model="claude-opus-4-5",
        provider="databricks"
    ),
    client=client
)

# 配置 A2A 能力
a2a_config = A2AAgentConfig(
    agent_name="math_expert",
    capabilities=[
        AgentCapability(
            name="solve_math",
            description="Solve mathematical problems",
            input_schema={
                "type": "object",
                "properties": {
                    "problem": {"type": "string"}
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "solution": {"type": "string"}
                }
            },
            tags=["math", "calculation"]
        )
    ]
)

# 创建 A2A 代理
a2a_agent = A2AAgent(base_agent, a2a_config)


# 注册能力处理器
@a2a_agent.handle_capability("solve_math")
async def handle_math(input_data):
    problem = input_data["problem"]
    # 使用基础代理解决问题
    solution = await base_agent.execute(problem)
    return {"solution": solution}


# 启动代理
await a2a_agent.start()
```

### 代理发现

发现具有特定能力的其他代理：

```python
from src.a2a import AgentRegistry, AgentDiscovery

# 创建共享注册表
registry = AgentRegistry()

# 创建发现服务
discovery = AgentDiscovery(registry)

# 发现具有特定能力的代理
agents = await discovery.discover(capabilities=["solve_math"])
for agent in agents:
    print(f"Found: {agent.agent_name} ({agent.agent_id})")

# 找到最佳代理
best_agent = await discovery.find_best_agent(
    capability="solve_math",
    criteria=lambda agent: len(agent.capabilities)  # 选择能力最多的
)
```

### 任务委托

将任务委托给其他代理：

```python
# 从一个代理委托任务给另一个代理
result = await agent1.delegate_task(
    target_agent_id=agent2.agent_id,
    capability="solve_math",
    input_data={"problem": "What is 15 * 23?"},
    timeout=30
)

if result.success:
    print(f"Solution: {result.output_data}")
else:
    print(f"Error: {result.error}")
```

使用任务委托服务进行自动代理选择：

```python
from src.a2a import TaskDelegation

delegation = TaskDelegation(discovery)

# 自动选择最佳代理并委托任务
result = await delegation.delegate_auto(
    capability="data_analysis",
    input_data={"dataset": "sales.csv"}
)

# 并行委托多个任务
tasks = [
    {"capability": "research", "input_data": {"topic": "AI"}},
    {"capability": "analyze", "input_data": {"data": "..."}},
    {"capability": "write", "input_data": {"outline": "..."}}
]
results = await delegation.delegate_parallel(tasks)
```

### 多代理协作

使用不同策略进行多代理协作：

#### 顺序协作

```python
from src.a2a import AgentCollaboration, CollaborationStrategy

# 创建顺序协作
collab = AgentCollaboration(strategy=CollaborationStrategy.SEQUENTIAL)

# 添加代理 (按执行顺序)
collab.add_agent(researcher_agent)
collab.add_agent(analyst_agent)
collab.add_agent(writer_agent)

# 执行协作任务
result = await collab.execute({
    "task": "create_report",
    "data": {"topic": "AI Trends 2024"}
})
```

#### 并行协作

```python
# 创建并行协作
collab = AgentCollaboration(strategy=CollaborationStrategy.PARALLEL)

# 添加代理 (并行执行)
collab.add_agent(agent1)
collab.add_agent(agent2)
collab.add_agent(agent3)

# 所有代理同时处理任务
result = await collab.execute({
    "task": "multi_perspective_analysis",
    "data": {"topic": "Market Trends"}
})
```

#### 共识协作

```python
# 创建共识协作
collab = AgentCollaboration(strategy=CollaborationStrategy.CONSENSUS)

# 添加代理
collab.add_agent(expert1)
collab.add_agent(expert2)
collab.add_agent(expert3)

# 通过投票达成共识
result = await collab.execute({
    "task": "make_decision",
    "data": {"question": "Should we proceed with this plan?"},
    "voting_method": "majority"  # or "unanimous", "weighted"
})

print(f"Decision: {result['decision']}")
```

使用共识构建器：

```python
from src.a2a import ConsensusBuilder

consensus = ConsensusBuilder(agents=[agent1, agent2, agent3])

decision = await consensus.reach_consensus(
    task="evaluate_proposal",
    input_data={"proposal": "..."},
    voting_method="weighted"
)
```

---

## 使用 Databricks Claude Opus 4.5 测试

### 环境配置

```bash
# 设置 Databricks 凭证
export DATABRICKS_API_KEY="dapi..."
export DATABRICKS_BASE_URL="https://your-workspace.cloud.databricks.com"
```

### 基础连接测试

```python
from src import UnifyLLM

# 初始化客户端
client = UnifyLLM(
    provider="databricks",
    api_key=os.getenv("DATABRICKS_API_KEY"),
    base_url=os.getenv("DATABRICKS_BASE_URL")
)

# 测试 Claude Opus 4.5
response = client.chat(
    model="claude-opus-4-5",  # 或您的端点名称
    messages=[
        {"role": "user", "content": "Hello!"}
    ],
    max_tokens=100
)

print(response.content)
```

### 运行测试套件

```bash
# 运行完整的 MCP 和 A2A 测试套件
python tests/test_mcp_a2a_databricks.py
```

测试包括：
1. ✅ Databricks Claude Opus 4.5 连接测试
2. ✅ MCP 服务器工具暴露测试
3. ✅ A2A 代理通信测试
4. ✅ 多代理协作测试 (顺序、并行、共识)

---

## 完整示例

### 示例 1: MCP 服务器暴露代理工具

```python
import asyncio
from src.mcp import MCPServer, MCPServerConfig, StdioTransport


async def main():
    # 创建服务器
    server = MCPServer(MCPServerConfig(server_name="agent-tools"))

    # 注册多个工具
    @server.tool("calculator", "Math calculations")
    async def calc(expr: str):
        return {"result": eval(expr)}

    @server.tool("text_processor", "Process text")
    async def process_text(text: str, operation: str):
        if operation == "uppercase":
            return {"result": text.upper()}
        elif operation == "lowercase":
            return {"result": text.lower()}
        return {"result": text}

    # 启动服务器
    transport = StdioTransport()
    await server.start(transport)


asyncio.run(main())
```

### 示例 2: A2A 多代理系统

```python
import asyncio
from src import UnifyLLM
from src.agent import Agent, AgentConfig
from src.a2a import (
    A2AAgent, A2AAgentConfig, AgentCapability,
    AgentRegistry, AgentCollaboration, CollaborationStrategy
)


async def main():
    # 创建共享注册表
    registry = AgentRegistry()

    # 创建三个专家代理
    agents = []
    for name in ["researcher", "analyst", "writer"]:
        # 基础 LLM 客户端
        client = UnifyLLM(
            provider="databricks",
            api_key="...",
            base_url="..."
        )

        # 基础代理
        base_agent = Agent(
            config=AgentConfig(
                name=name,
                model="claude-opus-4-5",
                provider="databricks",
                system_prompt=f"You are a {name} expert."
            ),
            client=client
        )

        # A2A 包装
        a2a_agent = A2AAgent(
            base_agent=base_agent,
            config=A2AAgentConfig(
                agent_name=name,
                capabilities=[
                    AgentCapability(
                        name=f"{name}_work",
                        description=f"Perform {name} work",
                        input_schema={"type": "object"},
                        output_schema={"type": "object"}
                    )
                ]
            ),
            registry=registry
        )

        await a2a_agent.start()
        agents.append(a2a_agent)

    # 创建协作工作流
    collab = AgentCollaboration(strategy=CollaborationStrategy.SEQUENTIAL)
    for agent in agents:
        collab.add_agent(agent)

    # 执行协作任务
    result = await collab.execute({
        "task": "create_comprehensive_report",
        "data": {"topic": "Future of AI Agents"}
    })

    print("Collaboration Result:", result)

    # 清理
    for agent in agents:
        await agent.stop()


asyncio.run(main())
```

### 示例 3: MCP + A2A 混合系统

```python
import asyncio
from src import UnifyLLM
from src.agent import Agent, AgentConfig
from src.mcp import MCPServer, MCPServerConfig
from src.a2a import A2AAgent, A2AAgentConfig, AgentCapability


async def main():
    # 1. 创建 MCP 服务器 (暴露工具)
    mcp_server = MCPServer(MCPServerConfig(server_name="shared-tools"))

    @mcp_server.tool("search_database", "Search in database")
    async def search_db(query: str):
        # 实际数据库查询逻辑
        return {"results": [...]}

    # 2. 创建 A2A 代理 (使用工具)
    client = UnifyLLM(provider="databricks", api_key="...", base_url="...")
    base_agent = Agent(
        config=AgentConfig(
            name="data_agent",
            model="claude-opus-4-5",
            provider="databricks"
        ),
        client=client
    )

    a2a_agent = A2AAgent(
        base_agent=base_agent,
        config=A2AAgentConfig(
            agent_name="data_agent",
            capabilities=[
                AgentCapability(
                    name="query_data",
                    description="Query and analyze data",
                    input_schema={"type": "object"},
                    output_schema={"type": "object"}
                )
            ]
        )
    )

    @a2a_agent.handle_capability("query_data")
    async def handle_query(input_data):
        # 代理可以使用 MCP 工具
        query = input_data.get("query")
        # 调用 MCP 工具
        results = await search_db(query)
        # 使用 LLM 分析结果
        analysis = await base_agent.execute(f"Analyze: {results}")
        return {"analysis": analysis}

    await a2a_agent.start()

    # 使用系统
    result = await a2a_agent.delegate_task(
        target_agent_id=a2a_agent.agent_id,
        capability="query_data",
        input_data={"query": "SELECT * FROM users"}
    )

    print("Result:", result)


asyncio.run(main())
```

---

## 最佳实践

### MCP 最佳实践

1. **工具设计**
   - 保持工具功能单一和专注
   - 提供清晰的输入/输出模式
   - 包含详细的描述和示例

2. **错误处理**
   - 在工具处理器中捕获异常
   - 返回有意义的错误消息
   - 实现重试逻辑

3. **性能**
   - 对于耗时操作使用异步
   - 实现超时机制
   - 考虑缓存常用结果

### A2A 最佳实践

1. **代理设计**
   - 为每个代理定义清晰的职责
   - 使用描述性的能力名称
   - 实现心跳机制保持活跃状态

2. **通信**
   - 使用共享注册表进行代理发现
   - 实现超时和重试逻辑
   - 考虑消息优先级

3. **协作**
   - 根据任务选择合适的协作策略
   - 实现任务分解和聚合
   - 处理部分失败情况

4. **安全性**
   - 验证代理身份
   - 限制敏感操作的访问
   - 记录所有代理间通信

---

## 故障排除

### MCP 常见问题

**问题**: 连接超时
**解决**: 检查传输配置，确保服务器正在运行

**问题**: 工具调用失败
**解决**: 验证输入模式，检查工具处理器的异常

### A2A 常见问题

**问题**: 找不到代理
**解决**: 确保代理已注册到注册表，检查心跳是否正常

**问题**: 任务委托超时
**解决**: 增加超时时间，检查目标代理状态

**问题**: 共识无法达成
**解决**: 调整投票方法，检查代理响应

---

## 更多资源

- [MCP 规范](https://modelcontextprotocol.io/)
- [UnifyLLM 文档](../README.md)
- [Databricks 代理指南](./DATABRICKS_AGENT_GUIDE.md)
- [示例代码](../scripts/examples/)
- [测试套件](../tests/test_mcp_a2a_databricks.py)

---

**更新日期**: 2026-01-07
**版本**: 1.0.0
