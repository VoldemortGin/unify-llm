# 0001 — Record architecture decisions with ADRs

## Status

Accepted

## Context

unify-llm is two things in one codebase: a unified LLM conversion library and a hidden-key
OpenAI-compatible proxy gateway. The non-obvious calls — why the gateway sits on a thin slice of
the package, why production hard-fails on a missing key, why upstream errors are never echoed, why
some legacy subtrees are exempt from the strict gate — are easy to erode once the original context
is lost. The repo is also navigated by AI agents that have no memory of prior conversations and
need a durable, greppable record of intent.

## Decision

We keep Architecture Decision Records under `docs/adr/`, one Markdown file per decision, named
`NNNN-kebab-title.md`. Each ADR uses a fixed shape: Title, **Status** (Accepted / Superseded /
Deprecated), **Context**, **Decision**, **Consequences**. ADRs are immutable once accepted — a
changed decision gets a new ADR that supersedes the old one rather than an in-place rewrite. ADRs
cross-reference each other by number (e.g. ADR-0007 builds on the factory seam of ADR-0006). The
root `CLAUDE.md` links here for rationale and stays a routing table, not a design doc.

## Consequences

- New contributors and agents can reconstruct *why*, not just *what*, from a single directory.
- A small discipline cost: a meaningful structural change should land with an ADR.
- The numbered, append-only history makes superseded decisions visible instead of silently lost.
