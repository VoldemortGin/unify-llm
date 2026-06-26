# 0004 — src layout + hatchling + uv + Python 3.13; ruff format replaces black

## Status

Accepted

## Context

The project needs a packaging and toolchain baseline that prevents accidental imports of an
uninstalled package, builds reproducibly, resolves dependencies fast, and lets the codebase use
modern typing without compatibility shims.

## Decision

- **src layout.** Code lives under `src/unify_llm/`; the wheel target is
  `packages = ["src/unify_llm"]`. Tests import the installed package, never a stray top-level dir.
- **hatchling** is the build backend (PEP 517/621 metadata in `pyproject.toml`).
- **uv** is the resolver/runner: `uv sync` for installs, `uv run` for every gated command. Dev
  tooling lives in a PEP 735 `dependency-group` (`dev`), which `uv sync` installs and `uv run`
  keeps by default — more stable than extras under `uv run`.
- **Python 3.13** is the floor (`requires-python = ">=3.13"`), so modern syntax (`X | Y`,
  `StrEnum`, `typing.override`) is available everywhere.
- **ruff format replaces black** as the single formatter, alongside ruff lint. Because 3.13 is the
  floor, `from __future__ import annotations` is dropped from modernized code.

## Consequences

- Deterministic, fast installs (`uv.lock`) and a single formatter shared by humans, CI, and the
  Docker build.
- Reproducible images: the Dockerfile uses pinned `uv` to build a self-contained `.venv`.
- The 3.13 floor is intentional and excludes older runtimes; legacy `from __future__` code remains
  only in the ratchet-exempt subtrees (ADR-0002).
