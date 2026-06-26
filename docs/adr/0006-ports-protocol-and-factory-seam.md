# 0006 — `ports/llm` Protocol + `ports/factory` as the unique assembly seam

## Status

Accepted

## Context

"Swap the model" must be a one-line change, not a refactor. If core/domain code imports vendor SDKs
or constructs providers ad hoc, every model switch ripples through call sites, and provider choice
plus key resolution scatter across the codebase. We want exactly one place that knows how to pick
an implementation and wire its real key.

## Decision

Two files own the seam:

- `ports/llm.py` defines the `LLMProvider` Protocol: a `@runtime_checkable`, structural,
  four-method contract — `chat`, `achat`, `chat_stream`, `achat_stream` — typed entirely against
  the canonical models of ADR-0003. Core/domain code depends on this Protocol and never imports a
  vendor SDK.
- `ports/factory.py` is the **unique assembly seam**. `REGISTRY` maps the 11 provider names to
  their adapter builders (plus the built-in `"mock"`). `make_llm(...)` is the model-agnostic entry
  point: it resolves the provider from argument / `APP_LLM_PROVIDER` / settings, pulls the real key
  via the registry, lazily constructs the chosen adapter, and can inject a shared HTTP client
  (ADR-0010). `build(provider, config)` is the pure table-lookup used by the `UnifyLLM` facade,
  which simply delegates here. Providers are imported by adapters, not by core; the facade does no
  construction logic of its own.

## Consequences

- Adding a model = registering one adapter row; call sites are untouched.
- Provider selection and key resolution live in one auditable place (foundation for ADR-0007).
- Structural typing keeps adapters decoupled while `mypy --strict` still checks the contract.
