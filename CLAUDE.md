# UnifyLLM Project Guide

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important (Claude Code Instructions)

* Break down each task into multiple simple sub-tasks (unless the task is already simple), then use a separate subagent for each task. Keep only necessary communication between subagent and main agent to save tokens.
* When using plan mode, don't skip details - break tasks down thoroughly so each sub-task is simple and clear.
* We're on Windows with PowerShell in PyCharm Terminal:
  * Prefer Python code for file operations (recommended, best cross-platform)
  * Use `rm` instead of `del` to delete files
  * Avoid non-GBK compatible unicode characters to prevent encoding errors
* Before developing, check if there's existing code in the codebase (especially under `unify_llm/`) to avoid reinventing the wheel.
* Don't auto-generate docs: No markdown files (README.md, summaries, etc.) unless explicitly requested. Keep the codebase clean.
* Put non-reusable code (examples, one-off tools) in `scripts/` folder. Tests go in `tests/`.

## Python Coding Standard

See [.claude/coding-standards.md](.claude/coding-standards.md) for details.

Key points:
1. Use Python 3.10+ type hints (`list[str]` not `List[str]`)
2. Import order: built-in > 3rd party > config > local
3. Stay simple, stay elegant
4. Cross-platform compatible (Windows + macOS)
5. Run all scripts from ROOT_DIR

---

## Project Overview

UnifyLLM is a unified LLM API library providing consistent interfaces (langchain format) for multiple providers.

**Core Value**:
- Unified interface for different LLM providers
- Easy switching between OpenAI, Anthropic, Gemini, Ollama
- Full support: sync/async, regular/streaming
- Production ready: error handling, retry, type checking

**Version**: 0.1.0 (Alpha) | **Python**: 3.10+ | **License**: MIT

## Project Structure

```
unify_llm/
  __init__.py              # Public API exports
  client.py                # UnifyLLM main client
  models.py                # Pydantic data models
  exceptions.py            # Exception definitions
  utils.py                 # Utility functions
  core/                    # Core infrastructure
    __init__.py
    config.py              # Configuration management
    db_config.py           # Database configuration
    logger.py              # Logging setup
  providers/               # Provider implementations
    __init__.py
    base.py                # BaseProvider abstract class
    openai.py              # OpenAI implementation
    anthropic.py           # Anthropic/Claude implementation
    gemini.py              # Google Gemini implementation
    ollama.py              # Ollama local models

tests/                     # Test files
scripts/                   # One-off scripts and examples
```

## Documentation

Detailed documentation is in `.claude/` folder:

- [Architecture](.claude/architecture.md) - Design patterns, data flow, module details
- [API Reference](.claude/api-reference.md) - Usage examples, common pitfalls
- [Development](.claude/development.md) - Adding providers, dev environment, tech stack
- [Coding Standards](.claude/coding-standards.md) - Python coding conventions

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Core | Pydantic 2.x | Data validation and models |
| HTTP | httpx | Sync/async HTTP requests |
| Retry | tenacity | Exponential backoff retry |
| Types | mypy (strict) | Static type checking |
| Test | pytest + pytest-asyncio | Unit and async tests |
| Quality | black + ruff | Formatting and linting |

## Quick Reference

### Environment Variables
```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
```

### Supported Models
- **OpenAI**: `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`
- **Anthropic**: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`
- **Gemini**: `gemini-pro`, `gemini-pro-vision`
- **Ollama**: `llama2`, `mistral`, `phi`, `codellama`, etc.

### Basic Usage
```python
from unify_llm import UnifyLLM

client = UnifyLLM(provider="openai")
response = client.chat(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.content)
```

---

**Last Updated**: 2025-12-29
