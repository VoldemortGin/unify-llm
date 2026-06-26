# 0007 — MockProvider is the keyless default; production hard-fails on a missing key

## Status

Accepted

## Context

The library and gateway must be runnable offline, in CI, and in fresh checkouts with no API keys —
otherwise tests and demos require secrets. But the same fallback that makes local life easy is
dangerous in production: a deployment that silently serves a deterministic Mock when its real key
is missing would look healthy while returning fake completions, hiding a misconfiguration until a
user notices.

## Decision

Resolution lives in `make_llm` at the single assembly seam (ADR-0006):

- Default provider is `"mock"` (see `Settings.llm_provider`); `MockProvider` needs no key and gives
  deterministic output, so offline/CI just works.
- When a key-requiring provider has **no** resolvable key, behaviour forks on environment:
  - **Non-production** (`APP_ENV != production`): fall back to the deterministic `MockProvider`.
  - **Production** (`APP_ENV == production`): raise `AuthenticationError` with a hint listing the
    expected env var(s). **Never** silently fall back to Mock.

The Dockerfile and `docker-compose.yml` pin `APP_ENV=production`, so deployments get the hard-fail
behaviour by default. `build()` (the facade path) does no Mock fallback at all — an explicitly
chosen provider is constructed as-is and reports a missing key at call time.

## Consequences

- Zero-friction local/CI runs; misconfiguration is loud, not silent, in production.
- The "fake answers" failure mode is structurally impossible in prod.
- Trade-off: the prod environment must set `APP_ENV=production` for the guard to engage — which the
  shipped Docker config does.
