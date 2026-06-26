# 0010 — OpenAI error envelope (never echo upstream) + process-level shared httpx client

## Status

Accepted

## Context

Two gateway concerns share one decision. First, leaking secrets through errors: an upstream
provider error can carry a real key in its text — e.g. Gemini puts the key in the URL query
(`?key=...`). Echoing upstream/unknown error bodies verbatim would leak the gateway's server-side
keys to clients. Second, connection lifecycle: constructing an `httpx` client per request (or per
provider) wastes connections, and an earlier pattern relied on `__del__` calling `asyncio.run`,
which is unsafe during interpreter shutdown.

## Decision

- **Error mapping.** `gateway/errors.py` maps the internal exception tree to the OpenAI envelope
  `{"error": {"message", "type", "code"}}`. Auth / rate-limit / request-validation errors (whose
  messages are gateway-generated and key-free) pass their message through. Upstream errors
  (`ProviderError` / `APIError`), transport errors (`httpx.RequestError`), and any unknown
  exception return a **generic** message ("Upstream provider error" / "Internal server error") —
  never the original text or a stack trace. This is the concrete enforcement of "upstream keys
  never leave the gateway" (see CLAUDE.md hard constraints; provider selection at ADR-0006).
- **Shared HTTP client.** The gateway lifespan creates exactly **one** process-level
  `httpx.AsyncClient` (pooled limits + timeouts), injected into providers via `make_llm`'s
  `http_client` parameter and closed on shutdown. The `__del__` + `asyncio.run` pattern is removed.

## Consequences

- Upstream/internal errors cannot leak keys, URLs, or stack traces to clients.
- Connection reuse cuts latency and fd churn; teardown is deterministic, not GC/`__del__`-timed.
- Clients see a stable, OpenAI-shaped error contract regardless of which upstream failed.
