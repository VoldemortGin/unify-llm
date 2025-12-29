# Development Guide

## Adding a New Provider

### 1. Create Provider Class

```python
# unify_llm/providers/myprovider.py
from .base import BaseProvider
from ..models import ChatRequest, ChatResponse, StreamChunk

class MyProvider(BaseProvider):
    def _get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.config.api_key}"}

    def _get_base_url(self) -> str:
        return "https://api.myprovider.com/v1"

    def _convert_request(self, request: ChatRequest) -> dict:
        # Convert to provider format
        pass

    def _convert_response(self, response: dict) -> ChatResponse:
        # Convert to unified format
        pass

    # ... implement other required methods
```

### 2. Register Provider

```python
# unify_llm/client.py
from .providers.myprovider import MyProvider

UnifyLLM.register_provider("myprovider", MyProvider)
```

### 3. Add Tests

```python
# tests/test_myprovider.py
def test_myprovider_chat():
    client = UnifyLLM(provider="myprovider", api_key="test")
    # ... test cases
```

## Development Environment

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Or use uv
uv pip install -e ".[dev]"
```

## Code Quality

```bash
# Format code
black unify_llm/

# Lint
ruff check unify_llm/

# Type check
mypy unify_llm/

# Run tests
pytest tests/ -v --cov=unify_llm
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Core | Pydantic 2.x | Data validation and models |
| HTTP | httpx | Sync/async HTTP requests |
| Retry | tenacity | Exponential backoff retry |
| Types | mypy (strict) | Static type checking |
| Test | pytest + pytest-asyncio | Unit and async tests |
| Quality | black + ruff | Formatting and linting |
| Build | setuptools | Package build and publish |

## Supported Models

- **OpenAI**: `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`
- **Anthropic**: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`
- **Gemini**: `gemini-pro`, `gemini-pro-vision`
- **Ollama**: `llama2`, `mistral`, `phi`, `codellama`, etc.

## Environment Variables

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
```
