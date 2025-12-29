# API Reference

## Basic Usage

```python
from unify_llm import UnifyLLM

# Initialize client
client = UnifyLLM(
    provider="openai",
    api_key="sk-...",  # or via env var OPENAI_API_KEY
)

# Sync chat
response = client.chat(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    temperature=0.7,
    max_tokens=1000
)
print(response.content)
```

## Async Usage

```python
import asyncio

async def main():
    client = UnifyLLM(provider="anthropic")

    response = await client.achat(
        model="claude-3-opus-20240229",
        messages=[{"role": "user", "content": "Explain quantum computing"}]
    )
    print(response.content)

asyncio.run(main())
```

## Streaming

```python
# Sync streaming
for chunk in client.chat_stream(
    model="gpt-4",
    messages=[{"role": "user", "content": "Tell a story"}]
):
    if chunk.content:
        print(chunk.content, end="", flush=True)

# Async streaming
async for chunk in client.achat_stream(
    model="claude-3-sonnet-20240229",
    messages=[{"role": "user", "content": "Write a poem"}]
):
    if chunk.content:
        print(chunk.content, end="", flush=True)
```

## Switching Providers

```python
# OpenAI
client = UnifyLLM(provider="openai")
response = client.chat(model="gpt-4", messages=[...])

# Claude
client = UnifyLLM(provider="anthropic")
response = client.chat(model="claude-3-opus-20240229", messages=[...])

# Gemini
client = UnifyLLM(provider="gemini")
response = client.chat(model="gemini-pro", messages=[...])

# Local Ollama
client = UnifyLLM(provider="ollama", base_url="http://localhost:11434")
response = client.chat(model="llama2", messages=[...])
```

## Error Handling

```python
from unify_llm import UnifyLLM, AuthenticationError, RateLimitError
import time

client = UnifyLLM(provider="openai")

try:
    response = client.chat(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}]
    )
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after} seconds")
    time.sleep(e.retry_after)
except Exception as e:
    print(f"Error: {e}")
```

## Using Message Objects

```python
from unify_llm import UnifyLLM, Message

messages = [
    Message(role="system", content="You are a coding assistant"),
    Message(role="user", content="Explain Python decorators"),
]

response = client.chat(model="gpt-4", messages=messages)
```

## Provider-Specific Parameters

```python
response = client.chat(
    model="gpt-4",
    messages=[...],
    provider_params={
        "logprobs": True,      # OpenAI specific
        "top_logprobs": 5,
    }
)
```

## Common Parameters

```python
chat(
    model: str,                    # Required: model name
    messages: list,                # Required: message list
    temperature: float = 1.0,      # 0.0-2.0
    max_tokens: int | None = None, # Max generation tokens
    top_p: float = 1.0,            # Nucleus sampling
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
    stop: list[str] | None = None, # Stop sequences
    stream: bool = False,          # Stream output
)
```

---

## Common Pitfalls

### 1. Anthropic max_tokens

```python
# WRONG: Anthropic requires max_tokens
response = client.chat(
    model="claude-3-opus-20240229",
    messages=[...]
)

# CORRECT
response = client.chat(
    model="claude-3-opus-20240229",
    messages=[...],
    max_tokens=4096  # Required
)
```

### 2. Gemini Role Names
- Internal auto-converts "assistant" -> "model"
- Users don't need to worry about this

### 3. Ollama Base URL
```python
# If Ollama runs on non-default port
client = UnifyLLM(
    provider="ollama",
    base_url="http://localhost:11434"  # Explicit
)
```

### 4. Stream Completion Check
```python
for chunk in client.chat_stream(model="gpt-4", messages=[...]):
    if chunk.content:
        print(chunk.content, end="")
    if chunk.finish_reason:
        print(f"\nFinish reason: {chunk.finish_reason}")
```

### 5. API Key Management
```python
# Prefer environment variables
# In .env file:
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GOOGLE_API_KEY=...

# No hardcoding needed
client = UnifyLLM(provider="openai")  # Auto reads from env
```

### 6. Async Resource Cleanup
```python
async def main():
    client = UnifyLLM(provider="openai")
    try:
        response = await client.achat(...)
    finally:
        del client  # Ensure cleanup
```
