# Python Coding Standards

## Type Hints

Use Python 3.10+ grammar for type hints:

```python
# Good
def process(items: list[str]) -> dict[str, int]: ...
def get_value() -> str | None: ...

# Avoid (old style)
from typing import List, Dict, Optional
def process(items: List[str]) -> Dict[str, int]: ...
```

## Import Order

Imports should follow this order: built-in > 3rd party > configuration > local

```python
import os

from dotenv import load_dotenv
import rootutils

ROOT_DIR = rootutils.setup_root(os.getcwd(), indicator='.project-root', pythonpath=True)
load_dotenv(ROOT_DIR / '.env')

from unify_llm.xxx import yyy
from unify_llm.zzz import www
```

## General Principles

1. **Stay Simple** - Don't over-design. Stay simple, stay elegant.
2. **Ask for Help** - If anything is unclear, don't guess, just ask.
3. **Read First** - Before coding, read `README.md` and `docs/` folder.
4. **Cross-Platform** - Code must work on both Windows and macOS.
5. **Run from ROOT_DIR** - Always run tests/scripts from the project root.

## Code Quality Tools

```bash
# Code formatting
black unify_llm/

# Linting
ruff check unify_llm/

# Type checking
mypy unify_llm/

# Run tests
pytest tests/ -v --cov=unify_llm
```
