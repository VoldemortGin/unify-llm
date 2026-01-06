# UnifyLLM

**统一的大语言模型接口调用框架**

UnifyLLM 是一个 Python 框架，提供统一的接口来调用各种大语言模型 API。通过 UnifyLLM，您可以使用相同的代码调用 OpenAI、Anthropic、Google Gemini、Ollama 等不同的 LLM 提供商。

## 核心特性

- ✅ **统一接口**: 所有 LLM 提供商使用相同的调用方式
- ✅ **多提供商支持**: OpenAI, Anthropic (Claude), Google Gemini, Ollama
- ✅ **流式/非流式**: 支持两种响应模式
- ✅ **同步/异步**: 完整支持同步和异步调用
- ✅ **错误处理**: 统一的异常类型和自动重试机制
- ✅ **类型提示**: 完整的 Python type hints
- ✅ **简单易用**: 最小化配置，开箱即用

## 安装

```bash
pip install unify_llm
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
from unify_llm import UnifyLLM

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
client = UnifyLLM(
    provider="databricks",
    api_key="dapi...",  # 或通过环境变量 DATABRICKS_API_KEY
    base_url="https://your-workspace.cloud.databricks.com/serving-endpoints"  # 或通过环境变量 DATABRICKS_BASE_URL
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
from unify_llm import UnifyLLM, AuthenticationError

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
from unify_llm import UnifyLLM
from unify_llm.providers import BaseProvider


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
black unify_llm tests
ruff check unify_llm tests
```

### 类型检查

```bash
mypy unify_llm
```

## 项目定位

UnifyLLM 专注于提供统一的 LLM API 调用接口，**不涉及**：

- ❌ Prompt 工程和模板
- ❌ RAG (检索增强生成)
- ❌ Agent 框架
- ❌ 向量数据库
- ❌ 高级工作流

如果您需要这些功能，请考虑使用 LangChain 或 LlamaIndex 等框架。

## 路线图

- [ ] 支持更多国内模型（智谱、文心、通义千问等）
- [ ] 支持 vLLM
- [ ] 函数调用（Function Calling）支持优化
- [ ] 批量请求优化
- [ ] 更详细的使用文档
- [ ] 性能基准测试

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
