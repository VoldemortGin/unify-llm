# 0003 — `models.py` is the single authoritative OpenAI-shaped schema

## Status

Accepted

## Context

A unified LLM library and an OpenAI-compatible gateway both need *one* data contract that every
provider adapter, the `LLMProvider` Protocol, and the gateway's HTTP ingress/egress agree on.
Without a single canonical schema, each adapter and each endpoint would invent overlapping shapes,
and the "OpenAI-compatible" promise would drift per provider.

## Decision

`src/unify_llm/models.py` holds the one authoritative, OpenAI-shaped schema, expressed as pydantic
v2 models: `ChatRequest`, `ChatResponse` (`ChatResponseChoice`), the streaming triple
`StreamChunk` / `StreamChoiceDelta` / `MessageDelta`, plus `Message`, `Usage`, `ProviderConfig`,
and the `Role` / `FinishReason` `StrEnum`s. The gateway ingress validates the request body as
`ChatRequest`; the egress serializes `ChatResponse` (non-stream) or emits OpenAI
`chat.completion.chunk` events from `StreamChunk` (stream). Every adapter parses its vendor wire
format *into* these models (parse-don't-validate) and renders *out of* them. This is the boundary
contract the `LLMProvider` Protocol is typed against (ADR-0006).

## Consequences

- One schema to evolve; a field added once is visible to every provider and both endpoints.
- "OpenAI-compatible" is structurally guaranteed, not per-adapter best-effort.
- pydantic validation at the boundary turns malformed input into typed errors, not late surprises.
- Cost: a breaking schema change is a coordinated change across all adapters — which is the point.
