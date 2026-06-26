# 0009 — Core leaf-ization + beartype claw hook (settings/import discipline)

## Status

Accepted

## Context

We want runtime type enforcement (beartype) across the whole package, installed via a claw hook in
`__init__.py`. A claw hook only instruments modules imported **after** it is installed. But the
hook's own configuration depends on a setting (`beartype_on`), which means *something* must be read
before the hook exists. If that something pulls in checked project modules, they get imported
pre-hook and silently escape instrumentation — a circular, order-dependent trap.

## Decision

`core/` is kept a **leaf**. `core/settings.py` is the single `APP_`-prefixed configuration source
(env + `.env` + `configs/settings.yaml` via pydantic-settings) and imports **only** stdlib +
pydantic / pydantic-settings — never a checked project module. The module-level `settings` instance
is built there. `__init__.py` then runs in a fixed order: import `settings` (the one allowed pre-
hook import, itself uninstrumented because it's a leaf), read `settings.beartype_on`, and install
the beartype claw hook (`beartype_this_package`) — full `On` strategy when `CI` is set, `O1`
sampling otherwise. Everything else, including the core symbols, is imported/exported lazily
(PEP 562 `__getattr__`) **after** the hook, so it all gets instrumented and bare `import unify_llm`
stays light.

## Consequences

- Every non-leaf module is born under runtime type-checking; the gate's beartype layer (ADR-0005)
  is real, not partial.
- The leaf rule is a hard invariant: making `core/settings.py` import a checked module reopens the
  hole. New settings keys go here, with no project imports.
