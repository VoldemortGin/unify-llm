# Architecture

## Design Patterns

The project uses **Provider Pattern** and **Factory Pattern**:

```
UnifyLLM (Client)
    |
BaseProvider (Abstract Base Class)
    |
OpenAI / Anthropic / Gemini / Ollama (Concrete Providers)
```

## Data Flow

```
User Request -> ChatRequest (Unified Format)
    |
Provider Convert (_convert_request)
    |
HTTP Request (Provider-specific Format)
    |
HTTP Response (Provider-specific Format)
    |
Response Convert (_convert_response)
    |
ChatResponse / StreamChunk (Unified Format)
```

## Core Modules

### 1. models.py - Data Models

**Core Models**:
- `Message`: Single message (role, content, name, tool_calls, etc.)
- `ChatRequest`: Unified chat request format
  - All parameters have validation (temperature 0-2, messages non-empty, etc.)
  - Supports provider-specific params via `provider_params`
- `ChatResponse`: Unified response format
  - Convenience properties: `.content`, `.finish_reason`
  - Includes usage stats and provider info
- `StreamChunk`: Streaming response chunk

**Validations**:
- `temperature`: Must be in 0.0-2.0 range
- `messages`: Cannot be empty
- `max_tokens`: Must be positive

### 2. client.py - UnifyLLM Client

**Init Parameters**:
```python
UnifyLLM(
    provider: str,           # "openai" | "anthropic" | "gemini" | "ollama"
    api_key: str | None,     # API key (can read from env)
    timeout: int = 60,       # Request timeout (seconds)
    max_retries: int = 3,    # Max retry count
    organization_id: str | None = None,  # Org ID (OpenAI only)
    extra_headers: dict | None = None,   # Extra headers
    base_url: str | None = None          # Custom base URL
)
```

**Four Call Methods**:
1. `chat()` - Sync chat
2. `achat()` - Async chat
3. `chat_stream()` - Sync streaming
4. `achat_stream()` - Async streaming

### 3. exceptions.py - Exception Hierarchy

```
UnifyLLMError (Base)
+-- AuthenticationError      # 401 Auth failed
+-- RateLimitError          # 429 Rate limit (has retry_after)
+-- InvalidRequestError     # 400/404/422 Invalid request
+-- APIError                # Generic API error
+-- TimeoutError            # 408 Timeout
+-- ModelNotFoundError      # 404 Model not found
+-- ContentFilterError      # 400 Content filtered
+-- ProviderError           # Provider-specific error
```

### 4. providers/base.py - Base Provider

**Core Responsibilities**:
- HTTP client management (sync `httpx.Client` and async `httpx.AsyncClient`)
- Auto retry mechanism (using `tenacity`)
- HTTP error handling and exception conversion
- Resource cleanup (`__del__` closes clients)

**Retry Config**:
- Exponential backoff: initial 1s, max 60s
- Max retries: configurable (default 3)
- Retry conditions: 5xx errors and 429 rate limit

**Required Methods**:
```python
def _get_headers(self) -> dict
def _get_base_url(self) -> str
def _convert_request(self, request: ChatRequest) -> dict
def _convert_response(self, response: dict) -> ChatResponse
def _convert_stream_chunk(self, chunk: dict) -> StreamChunk
def _chat_impl(self, endpoint: str, request: dict) -> dict
async def _achat_impl(self, endpoint: str, request: dict) -> dict
def _chat_stream_impl(self, endpoint: str, request: dict) -> Iterator
async def _achat_stream_impl(self, endpoint: str, request: dict) -> AsyncIterator
```

### 5. Provider Implementations

#### OpenAI (openai.py)
- **Endpoint**: `https://api.openai.com/v1/chat/completions`
- **Auth**: Bearer Token
- **Special**: Supports org ID, SSE streaming, ends with `data: [DONE]`

#### Anthropic (anthropic.py)
- **Endpoint**: `https://api.anthropic.com/v1/messages`
- **Auth**: `x-api-key` header
- **Special**: System message needs separate `system` param, `max_tokens` required (default 4096)

#### Gemini (gemini.py)
- **Endpoint**: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- **Auth**: URL query param `?key={api_key}`
- **Special**: Uses `contents` array, role mapping (assistant -> model)

#### Ollama (ollama.py)
- **Endpoint**: `http://localhost:11434/api/chat` (configurable)
- **Auth**: Optional API key
- **Special**: Params in `options` object, uses `num_predict` instead of `max_tokens`

### 6. utils.py - Utilities

```python
get_api_key_from_env(provider: str) -> str | None
    # Read API key from env: {PROVIDER}_API_KEY

estimate_tokens(text: str) -> int
    # Rough estimate: ~4 chars = 1 token

truncate_messages(messages: list[Message], max_tokens: int) -> list[Message]
    # Truncate to fit token limit, keeps system messages

format_provider_error(error: Exception, provider: str) -> str
    # Format provider error message
```

## Design Principles

1. **Unified First** - All providers use same `ChatRequest` and `ChatResponse` format
2. **Type Safe** - Pydantic validation, full type annotations (mypy strict)
3. **Error Handling** - Fine-grained exceptions, auto retry with exponential backoff
4. **Extensible** - Provider registration, custom base URLs, provider-specific params
5. **Async First** - Full asyncio support with `httpx` async client
