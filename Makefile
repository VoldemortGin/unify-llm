.PHONY: help install check fmt test clean

help:
	@echo "unify-llm — dev commands"
	@echo "  make install   uv sync (editable install + dev group)"
	@echo "  make check     one-command zero-warning gate (ruff fmt + ruff + mypy + pytest)"
	@echo "  make fmt       auto-format + autofix (ruff)"
	@echo "  make test      run tests (beartype O1 locally)"
	@echo "  make clean     remove caches / build artifacts"

install:
	uv sync

# 唯一的零警告门:人与 agent 共用的"是否完成"判据。任一步非零即整体失败。
check:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy src
	uv run pytest

fmt:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/ .mypy_cache .ruff_cache
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
