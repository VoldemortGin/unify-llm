.PHONY: help install install-dev test test-verbose test-cov lint format type-check clean build publish docs serve-docs

# Default target
help:
	@echo "UnifyLLM Development Commands"
	@echo "=============================="
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install package in production mode"
	@echo "  make install-dev    Install package in development mode with dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run unit tests (exclude integration tests)"
	@echo "  make test-verbose   Run unit tests with verbose output"
	@echo "  make test-cov       Run unit tests with coverage report"
	@echo "  make test-all       Run all tests including integration tests"
	@echo "  make test-integration  Run only integration tests (calls real LLM APIs)"
	@echo "  make test-watch     Run tests in watch mode (requires pytest-watch)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           Run linter (ruff)"
	@echo "  make format         Format code (black)"
	@echo "  make format-check   Check code formatting without changes"
	@echo "  make type-check     Run type checker (mypy)"
	@echo "  make quality        Run all quality checks (format-check, lint, type-check)"
	@echo ""
	@echo "Build & Publish:"
	@echo "  make clean          Clean build artifacts"
	@echo "  make build          Build distribution packages"
	@echo "  make publish        Publish to PyPI"
	@echo "  make publish-test   Publish to TestPyPI"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs           Build documentation"
	@echo "  make serve-docs     Serve documentation locally"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean-cache    Clean Python cache files"
	@echo "  make clean-all      Clean all generated files"

# Setup
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

# Testing
test:
	pytest -m "not integration"

test-verbose:
	pytest -v -m "not integration"

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term-missing -m "not integration"

test-all:
	pytest

test-integration:
	@echo "⚠️  WARNING: This will call real LLM APIs and may incur costs!"
	@echo "Make sure you have set the required API keys in your environment."
	@echo ""
	pytest -v -m "integration"

test-watch:
	pytest-watch

# Code Quality
lint:
	ruff check src tests

lint-fix:
	ruff check --fix src tests

format:
	black src tests

format-check:
	black --check src tests

type-check:
	mypy src

quality: format-check lint type-check
	@echo "All quality checks passed!"

# Build & Publish
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache
	rm -rf .ruff_cache

clean-cache:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.py~" -delete

clean-all: clean clean-cache

build: clean
	python -m build

publish: build
	twine upload dist/*

publish-test: build
	twine upload --repository testpypi dist/*

# Documentation
docs:
	@echo "Documentation building not yet configured"
	@echo "Consider adding sphinx or mkdocs"

serve-docs:
	@echo "Documentation serving not yet configured"
	@echo "Consider adding sphinx or mkdocs"

# Development utilities
run-example:
	python scripts/basic_usage.py

run-agent-example:
	python scripts/examples/agent_basic.py

check-deps:
	pip list --outdated

update-deps:
	pip install --upgrade -e ".[dev]"
