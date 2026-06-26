"""Conformance kit(ADR-05):一组不变量,parametrized 跑过所有 adapter(含 Mock)。

用 httpx.MockTransport 模拟各家响应,不连真网络、不需要真 key。对每个 adapter 断言同一组
行为契约:
  - chat(req) 返回合法 ChatResponse;
  - chat_stream(req) 产出合法 StreamChunk;
  - 厂商网络错(MockTransport 抛 httpx.ConnectError)→ 归一为 ProviderError;
  - 401 响应 → AuthenticationError;
  - 每个实现 isinstance(impl, LLMProvider)(runtime_checkable 结构判定)。

各家响应/流式 wire 形状不同,故每个 case 自带其专属 mock 载荷;断言的是统一后的不变量。
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

import httpx
import pytest

from unify_llm.adapters.mock import MockProvider
from unify_llm.core.exceptions import AuthenticationError, ProviderError
from unify_llm.models import ChatRequest, ChatResponse, Message, ProviderConfig, StreamChunk
from unify_llm.ports import factory
from unify_llm.ports.llm import LLMProvider

# ── 各家 mock wire 载荷 ──────────────────────────────────────────────────────

# OpenAI 兼容族(openai/grok/openrouter/bytedance/deepseek/databricks/anthropic_openai 共用)
_OPENAI_CHAT: dict[str, object] = {
    "id": "c",
    "model": "m",
    "choices": [
        {"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}
    ],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}
_OPENAI_STREAM = (
    b'data: {"id":"c","model":"m","choices":[{"index":0,'
    b'"delta":{"role":"assistant","content":"hi"}}]}\n\n'
    b"data: [DONE]\n\n"
)

_ANTHROPIC_CHAT: dict[str, object] = {
    "id": "a",
    "model": "m",
    "content": [{"type": "text", "text": "hi"}],
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 1, "output_tokens": 1},
}
_ANTHROPIC_STREAM = (
    b'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"hi"}}\n\n'
)

_GEMINI_CHAT: dict[str, object] = {
    "candidates": [{"content": {"parts": [{"text": "hi"}]}, "finishReason": "STOP"}],
    "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2},
    "modelVersion": "m",
}
_GEMINI_STREAM = b'{"candidates":[{"content":{"parts":[{"text":"hi"}]}}],"modelVersion":"m"}\n'

_QWEN_CHAT: dict[str, object] = {
    "output": {
        "choices": [{"message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}]
    },
    "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
    "request_id": "r",
}
_QWEN_STREAM = (
    b'data:{"output":{"choices":[{"message":{"role":"assistant","content":"hi"},'
    b'"finish_reason":"stop"}]},"request_id":"r"}\n'
)

_OLLAMA_CHAT: dict[str, object] = {
    "model": "m",
    "message": {"role": "assistant", "content": "hi"},
    "done": True,
    "prompt_eval_count": 1,
    "eval_count": 1,
}
_OLLAMA_STREAM = (
    b'{"model":"m","message":{"content":"hi"},"done":false}\n'
    b'{"model":"m","message":{"content":""},"done":true}\n'
)


@dataclass(frozen=True)
class Case:
    """一个 adapter 的 conformance 用例(名字 + 专属 mock 载荷 + 可选 base_url)。"""

    name: str
    chat_json: dict[str, object]
    stream_body: bytes
    base_url: str | None = None


_OPENAI_COMPAT_NAMES = (
    "openai",
    "grok",
    "openrouter",
    "bytedance",
    "deepseek",
    "anthropic_openai",
)

CASES: list[Case] = [
    *[Case(n, _OPENAI_CHAT, _OPENAI_STREAM) for n in _OPENAI_COMPAT_NAMES],
    # databricks 无静态默认 base_url,需显式提供(否则 httpx 拒绝相对 URL)。
    Case("databricks", _OPENAI_CHAT, _OPENAI_STREAM, base_url="https://dbx.example.com"),
    Case("anthropic", _ANTHROPIC_CHAT, _ANTHROPIC_STREAM),
    Case("gemini", _GEMINI_CHAT, _GEMINI_STREAM),
    Case("qwen", _QWEN_CHAT, _QWEN_STREAM),
    Case("ollama", _OLLAMA_CHAT, _OLLAMA_STREAM),
]

_IDS = [c.name for c in CASES]


# ── helpers ─────────────────────────────────────────────────────────────────


def _build(case: Case) -> LLMProvider:
    """构造 provider 并立即关闭其真实 HTTP 客户端(测试只用注入的 MockTransport)。"""
    provider = factory.build(case.name, ProviderConfig(api_key="test-key", base_url=case.base_url))
    # 关掉 __init__ 起的真实客户端,避免未关连接告警。
    if hasattr(provider, "client"):
        provider.client.close()  # type: ignore[attr-defined]
    if hasattr(provider, "async_client"):
        asyncio.run(provider.async_client.aclose())  # type: ignore[attr-defined]
    return provider


def _patch(provider: LLMProvider, handler: Callable[[httpx.Request], httpx.Response]) -> None:
    provider.client = httpx.Client(transport=httpx.MockTransport(handler))  # type: ignore[attr-defined]


def _request() -> ChatRequest:
    return ChatRequest(model="m", messages=[Message(role="user", content="ping")])


def _ok(payload: dict[str, object]) -> Callable[[httpx.Request], httpx.Response]:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return handler


def _stream_ok(body: bytes) -> Callable[[httpx.Request], httpx.Response]:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    return handler


def _unauthorized(request: httpx.Request) -> httpx.Response:
    return httpx.Response(401, json={"error": "invalid api key"})


def _connect_error(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("simulated connect failure", request=request)


# ── invariants ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("case", CASES, ids=_IDS)
def test_isinstance_protocol(case: Case) -> None:
    provider = _build(case)
    try:
        assert isinstance(provider, LLMProvider)
    finally:
        provider.client.close()  # type: ignore[attr-defined]


def test_mock_isinstance_protocol() -> None:
    assert isinstance(MockProvider(), LLMProvider)


@pytest.mark.parametrize("case", CASES, ids=_IDS)
def test_chat_returns_valid_response(case: Case) -> None:
    provider = _build(case)
    _patch(provider, _ok(case.chat_json))
    try:
        resp = provider.chat(_request())
        assert isinstance(resp, ChatResponse)
        assert resp.content == "hi"
        assert resp.choices
    finally:
        provider.client.close()  # type: ignore[attr-defined]


@pytest.mark.parametrize("case", CASES, ids=_IDS)
def test_chat_stream_yields_chunks(case: Case) -> None:
    provider = _build(case)
    _patch(provider, _stream_ok(case.stream_body))
    try:
        chunks = list(provider.chat_stream(_request()))
        assert chunks
        assert all(isinstance(c, StreamChunk) for c in chunks)
        assert "".join(c.content or "" for c in chunks) == "hi"
    finally:
        provider.client.close()  # type: ignore[attr-defined]


@pytest.mark.parametrize("case", CASES, ids=_IDS)
def test_401_maps_to_authentication_error(case: Case) -> None:
    provider = _build(case)
    _patch(provider, _unauthorized)
    try:
        with pytest.raises(AuthenticationError):
            provider.chat(_request())
    finally:
        provider.client.close()  # type: ignore[attr-defined]


@pytest.mark.parametrize("case", CASES, ids=_IDS)
def test_network_error_maps_to_provider_error(case: Case) -> None:
    provider = _build(case)
    _patch(provider, _connect_error)
    try:
        with pytest.raises(ProviderError):
            provider.chat(_request())
    finally:
        provider.client.close()  # type: ignore[attr-defined]


# ── Mock provider(无 HTTP,直接验证不变量)──────────────────────────────────


def test_mock_chat_and_stream_offline() -> None:
    provider = MockProvider()
    resp = provider.chat(_request())
    assert isinstance(resp, ChatResponse)
    assert resp.provider == "mock"
    assert resp.content is not None

    chunks = list(provider.chat_stream(_request()))
    assert chunks
    assert all(isinstance(c, StreamChunk) for c in chunks)
    assert "".join(c.content or "" for c in chunks) == resp.content
