# 0005 — One-command zero-warning gate, plus a ratchet for legacy

## Status

Accepted

## Context

"Done" must mean the same thing for a human and for an AI agent, and it must be checkable in one
command with no judgement calls. At the same time, the repo carries legacy subtrees (ADR-0002)
that cannot pass a strict gate today. A gate that fails on day-one legacy would be ignored; a gate
that's lenient on new code would never raise the bar.

## Decision

There is exactly one gate: `make check`, four steps, fail-fast, zero-warning:

1. `ruff format --check .` — formatting enforced.
2. `ruff check .` — lint rules `E F I UP ANN B SIM RUF` (including `ANN` annotation coverage).
3. `mypy src` — `strict = true` (+ `warn_unreachable`, `warn_return_any`).
4. `pytest` — `filterwarnings = error` (warnings-as-errors) with **beartype** runtime
   type-checking active (`O1` sampling locally, full `On` when `CI` is set, see ADR-0009).

It is the same gate run locally, in CI, and pre-push. Layered on top is a **ratchet**: new and
modernized code is born green under the full gate, while the legacy subtrees
(`agent/`, `mcp/`, `a2a`, `langchain_adapter.py`, listed legacy tests/scripts) are explicitly
exempted in `pyproject.toml` (`ruff extend-exclude`, `mypy overrides ignore_errors`). The exempt
list only ever shrinks.

## Consequences

- One unambiguous "is it done" signal; agents can self-verify without human review.
- The project ships now without a big-bang rewrite, while debt is fenced and visible.
- Discipline required: never widen the exempt list to dodge the gate; modernize, then remove the
  exemption.
