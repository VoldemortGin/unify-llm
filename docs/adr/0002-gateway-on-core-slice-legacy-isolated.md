# 0002 — Gateway builds on the core+models+providers slice; legacy isolated as optional extras

## Status

Accepted

## Context

The repository accumulated several subsystems beyond the conversion core: `agent/` (scheduling),
`mcp/`, `a2a/`, and `langchain_adapter.py`. These predate the current type/lint discipline and
carry `from __future__` imports and legacy typing. The Phase-4 deliverable — the production proxy
gateway — must not inherit that debt, nor force a risky big-bang rewrite of everything before it
can ship.

## Decision

The gateway (`gateway/`) depends only on a clean, modernized slice of the package:
`core/` (settings, exceptions), `models.py` (the canonical schema), `ports/` (the `LLMProvider`
Protocol and `factory`), and `adapters/` (the providers + Mock). `agent/`, `mcp/`, `a2a`, and
`langchain_adapter.py` are treated as **optional extras**: still importable, still tested in their
own lane, but **isolated** from the gateway's dependency graph and from the strict gate via
`pyproject.toml` (`tool.ruff` `extend-exclude` and `tool.mypy.overrides` `ignore_errors`). They are
deliberately **not deleted** — they hold real, working functionality to be modernized later
(see the ratchet in ADR-0005).

## Consequences

- The gateway ships on a small, fully strict surface without waiting on legacy cleanup.
- Legacy capability is preserved and can be modernized module-by-module, then folded back into the
  gate.
- Cost: two tiers of code coexist; the boundary must be respected so debt does not leak into the
  strict slice.
