# 0008 — OpenAI-compatible family merged behind a data registry; others standalone

## Status

Accepted

## Context

Several providers — OpenAI, Grok (x.ai), OpenRouter, ByteDance (Volcengine Ark), DeepSeek — speak
field-for-field OpenAI chat-completions. Implementing one adapter class per vendor duplicated the
same request/response/stream translation five times, so a bug fix or schema tweak had to be applied
in five places. Other providers (Qwen, Anthropic, Gemini) have genuinely different wire formats and
do not fit that mold.

## Decision

In `adapters/openai_compatible.py` the OpenAI-compatible family collapses to **one**
`OpenAICompatibleProvider` plus a **data registry** `OPENAI_COMPAT_SPECS`. Each vendor is a single
`OpenAICompatSpec` row capturing only its differences — `base_url`, key env var, default model, and
small flags like `coerce_empty_content` (ByteDance) or `default_headers` (OpenRouter). The named
subclasses (`OpenAIProvider`, `GrokProvider`, `OpenRouterProvider`, `ByteDanceProvider`,
`DeepSeekProvider`) just bind their spec, preserving backward-compatible imports and a uniform
`cls(config)` shape for the factory `REGISTRY`. Adding a compatible vendor = adding one spec row,
not a new class. Providers whose formats genuinely differ — `qwen.py`, `anthropic.py`,
`gemini.py` (and `ollama.py`, `databricks.py`, `anthropic_openai.py`) — remain **standalone**
adapters with their own translation.

## Consequences

- One implementation, one place to fix, for the whole compatible family.
- New compatible vendors are near-zero-cost; truly different ones still get bespoke adapters.
- The factory registry (ADR-0006) sees a uniform builder shape across both styles.
