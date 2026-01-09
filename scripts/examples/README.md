# Examples Directory

This directory contains comprehensive examples demonstrating MCP and A2A protocol usage with UnifyLLM.

## 📚 Available Examples

### 1. End-to-End Demo (⭐ Recommended Start Here)
**File**: `demo_end_to_end.py`

A complete demonstration of 4 AI agents working together:
- **Code Analyzer**: Analyzes code quality and complexity
- **Security Auditor**: Checks for vulnerabilities
- **Documentation Writer**: Generates documentation
- **Coordinator**: Manages the workflow

**Features Demonstrated**:
- ✅ Multiple specialized agents
- ✅ A2A task delegation
- ✅ Message bus communication
- ✅ Multi-agent collaboration with consensus
- ✅ Complete workflow orchestration

**Run**:
```bash
python examples/demo_end_to_end.py
```

**Output**: Shows a complete code analysis workflow with quality scoring, security audit, and documentation generation.

---

### 2. Quick Start Guide
**File**: `quickstart_mcp_a2a.py`

Introduction to MCP and A2A features with simple examples:
- Basic MCP server creation
- A2A agent communication
- Multi-agent collaboration strategies

**Features Demonstrated**:
- ✅ MCP server setup
- ✅ A2A agent creation
- ✅ Agent discovery
- ✅ Sequential, parallel, and consensus collaboration

**Run**:
```bash
python examples/quickstart_mcp_a2a.py
```

---

### 3. MCP File System Server
**File**: `mcp_server_filesystem.py`

Production-ready MCP server that exposes file system operations as tools.

**Tools Provided**:
- `list_directory`: List directory contents
- `read_file`: Read text files
- `write_file`: Write to files
- `search_files`: Search with glob patterns

**Resources Provided**:
- `file://cwd`: Current working directory
- `system://env`: Environment information

**Prompts Provided**:
- `summarize_file`: File summary template

**Run**:
```bash
python examples/mcp_server_filesystem.py
```

**Use Case**: Start this server and connect MCP clients to it for file operations.

---

### 4. MCP Client Integration
**File**: `mcp_client_integration.py`

Demonstrates how to integrate MCP clients with AI agents.

**Features Demonstrated**:
- ✅ Connecting agents to MCP servers
- ✅ Using MCP tools from agents
- ✅ Combining MCP with A2A capabilities
- ✅ Multi-server scenarios
- ✅ `MCPIntegratedAgent` helper class

**Run**:
```bash
python examples/mcp_client_integration.py
```

---

## 🚀 Getting Started

### Prerequisites

1. **Install UnifyLLM**:
   ```bash
   cd /path/to/unify-llm
   pip install -e .
   ```

2. **Set Databricks Credentials** (optional, examples work in demo mode):
   ```bash
   export DATABRICKS_API_KEY="dapi..."
   export DATABRICKS_BASE_URL="https://your-workspace.cloud.databricks.com"
   ```

### Recommended Learning Path

1. **Start with**: `demo_end_to_end.py`
   - See everything working together
   - Understand the complete workflow

2. **Then try**: `quickstart_mcp_a2a.py`
   - Learn individual components
   - Understand basic patterns

3. **Explore**: `mcp_server_filesystem.py`
   - See production MCP server
   - Understand tool registration

4. **Finally**: `mcp_client_integration.py`
   - Learn advanced integration
   - Combine MCP + A2A

---

## 💡 Example Use Cases

### Use Case 1: Code Analysis Pipeline
Run `demo_end_to_end.py` to see how multiple agents can collaborate on code analysis, security auditing, and documentation generation.

### Use Case 2: File Operations
Run `mcp_server_filesystem.py` to expose file system operations that any MCP client (including AI agents) can use.

### Use Case 3: Multi-Agent System
Adapt `quickstart_mcp_a2a.py` to create your own team of specialized agents for your domain.

### Use Case 4: Tool Integration
Use `mcp_client_integration.py` as a template to connect your agents to external tools via MCP.

---

## 🔧 Customization

### Adding Your Own Agents

```python
from src import UnifyLLM
from src.agent import Agent, AgentConfig
from src.a2a import A2AAgent, A2AAgentConfig, AgentCapability

# Create your specialized agent
client = UnifyLLM(provider="databricks", ...)
base_agent = Agent(config=AgentConfig(
    name="my_specialist",
    model="claude-opus-4-5",
    system_prompt="You are a specialist in X"
))

# Wrap with A2A capabilities
a2a_agent = A2AAgent(
    base_agent,
    A2AAgentConfig(
        agent_name="my_specialist",
        capabilities=[AgentCapability(name="my_skill", ...)]
    )
)


# Register capability handler
@a2a_agent.handle_capability("my_skill")
async def handle_my_skill(input_data):
    # Your logic here
    return {"result": ...}
```

### Creating Custom MCP Tools

```python
from src.mcp import MCPServer, MCPServerConfig

server = MCPServer(MCPServerConfig(server_name="my-tools"))


@server.tool("my_tool", "Description of what it does")
async def my_tool(param1: str, param2: int) -> dict:
    # Your tool logic
    return {"result": ...}
```

---

## 📖 Additional Resources

- **Complete Guide**: `../docs/MCP_A2A_GUIDE.md`
- **API Documentation**: `../README.md`
- **Test Suite**: `../tests/test_mcp_a2a_databricks.py`
- **Databricks Guide**: `../docs/DATABRICKS_AGENT_GUIDE.md`

---

## 🐛 Troubleshooting

### "Module not found" errors
Make sure you've installed UnifyLLM:
```bash
pip install -e .
```

### Examples run in demo mode
This is normal if you haven't set Databricks credentials. The examples simulate agent behavior.

To use real Databricks Claude Opus 4.5:
```bash
export DATABRICKS_API_KEY="your-key"
export DATABRICKS_BASE_URL="your-url"
```

### Import errors
Ensure you're running from the project root:
```bash
cd /path/to/unify-llm
python examples/demo_end_to_end.py
```

---

## 🤝 Contributing

Have a great example? Please contribute!

1. Create your example in `examples/`
2. Add documentation here
3. Submit a pull request

---

## 📊 Example Complexity

| Example | Complexity | Lines | Best For |
|---------|-----------|-------|----------|
| demo_end_to_end.py | Advanced | ~500 | Seeing everything together |
| quickstart_mcp_a2a.py | Beginner | ~300 | Learning basics |
| mcp_server_filesystem.py | Intermediate | ~350 | MCP server development |
| mcp_client_integration.py | Intermediate | ~300 | Integration patterns |

---

**Happy coding with MCP & A2A! 🚀**
