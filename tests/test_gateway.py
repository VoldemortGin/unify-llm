"""网关测试:同步 FastAPI TestClient + MockProvider,全程不连真网络。

每个用例用 helper 现造一个**全新** app(故内存限流器彼此隔离),并一律以 ``with TestClient(app)``
驱动(跑 lifespan,建/关进程级共享 httpx 客户端,免 filterwarnings=error 下的未关连接告警)。
鉴权 / 限流 / 路由跑的是真实代码,只有最终 LLM 调用被 Mock 顶替。
"""

import warnings

import httpx
import pytest
from fastapi import FastAPI
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from unify_llm.adapters.mock import MockProvider
from unify_llm.core.exceptions import ProviderError
from unify_llm.gateway.app import ProviderFactory, create_app
from unify_llm.gateway.config import AppKey, GatewayConfig, ModelRoute, hash_app_key
from unify_llm.models import ChatRequest, ChatResponse

with warnings.catch_warnings():
    # starlette 1.3 在未装 httpx2 时于 import 期发一次性 DeprecationWarning(纯测试客户端、与本端
    # 代码无关)。局部静默这一次导入告警,绝不放宽全局 filterwarnings=error 门。
    warnings.simplefilter("ignore")
    from fastapi.testclient import TestClient

_AUTH = {"Authorization": "Bearer test-app-key"}


def _config(rate_limit_rpm: int = 60, budget_usd: float | None = None) -> GatewayConfig:
    """造一份测试网关配置:应用 key 明文 ``test-app-key``,只允许 ``mock-model``。"""
    return GatewayConfig(
        app_keys=[
            AppKey(
                app_id="test",
                key_sha256=hash_app_key("test-app-key"),
                allowed_models=["mock-model"],
                rate_limit_rpm=rate_limit_rpm,
                rate_limit_tpm=100_000,
                budget_usd=budget_usd,
            )
        ],
        models={
            "mock-model": ModelRoute(
                provider="mock",
                upstream_model="mock-upstream",
                input_price_per_1k=1.0,
                output_price_per_1k=2.0,
            ),
            # 可路由但不在白名单内的第二个模型(用于 403 用例)。
            "secret-model": ModelRoute(provider="mock", upstream_model="x"),
        },
    )


def _mock_factory(name: str, client: httpx.AsyncClient) -> MockProvider:
    """注入工厂:让 LLM 调用走确定性 Mock(鉴权/限流/路由仍跑真代码)。"""
    return MockProvider()


class _BoomProvider(MockProvider):
    """achat 抛 ProviderError 的 Mock,用于验证上游错 → 502 且不泄上游 key。"""

    async def achat(self, request: ChatRequest, /) -> ChatResponse:
        raise ProviderError("upstream boom", provider="openai")


def _boom_factory(name: str, client: httpx.AsyncClient) -> _BoomProvider:
    return _BoomProvider()


def _app(config: GatewayConfig | None = None, factory: ProviderFactory | None = None) -> FastAPI:
    cfg = config if config is not None else _config()
    make = factory if factory is not None else _mock_factory
    return create_app(cfg, make_provider=make)


def _chat_body(model: str, *, stream: bool = False) -> dict[str, object]:
    return {"model": model, "messages": [{"role": "user", "content": "ping"}], "stream": stream}


def test_healthz_no_auth() -> None:
    with TestClient(_app()) as client:
        resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_requires_auth_401() -> None:
    with TestClient(_app()) as client:
        resp = client.post("/v1/chat/completions", json=_chat_body("mock-model"))
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["type"] == "authentication_error"
    assert "message" in body["error"]


def test_chat_non_stream_200() -> None:
    with TestClient(_app()) as client:
        resp = client.post("/v1/chat/completions", headers=_AUTH, json=_chat_body("mock-model"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "chat.completion"
    # 公开 model id 还原(上游真实 model 对客户端隐藏)。
    assert data["model"] == "mock-model"
    assert data["choices"][0]["message"]["content"]
    assert "raw_response" not in data


def test_chat_stream_200() -> None:
    with TestClient(_app()) as client:
        resp = client.post(
            "/v1/chat/completions", headers=_AUTH, json=_chat_body("mock-model", stream=True)
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert "data: " in resp.text
    assert resp.text.rstrip().endswith("data: [DONE]")


def test_rate_limit_429() -> None:
    with TestClient(_app(_config(rate_limit_rpm=1))) as client:
        first = client.post("/v1/chat/completions", headers=_AUTH, json=_chat_body("mock-model"))
        assert first.status_code == 200
        second = client.post("/v1/chat/completions", headers=_AUTH, json=_chat_body("mock-model"))
    assert second.status_code == 429
    assert "Retry-After" in second.headers
    assert second.json()["error"]["type"] == "rate_limit_error"


def test_unauthorized_model_403() -> None:
    with TestClient(_app()) as client:
        resp = client.post("/v1/chat/completions", headers=_AUTH, json=_chat_body("secret-model"))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "model_not_allowed"


def test_unknown_model_404() -> None:
    cfg = _config()
    # 把一个不可路由的 model 加进白名单:过得了白名单校验,却查不到路由 → 404。
    cfg.app_keys[0].allowed_models.append("ghost-model")
    with TestClient(_app(cfg)) as client:
        resp = client.post("/v1/chat/completions", headers=_AUTH, json=_chat_body("ghost-model"))
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "model_not_found"


def test_upstream_error_502_no_key_leak(monkeypatch: pytest.MonkeyPatch) -> None:
    # 真实上游 key 在 env 里;断言它绝不出现在网关响应里(证明上游 key 永不进响应)。
    monkeypatch.setenv("OPENAI_API_KEY", "sk-SECRET-LEAK-CANARY")
    with TestClient(_app(factory=_boom_factory)) as client:
        resp = client.post("/v1/chat/completions", headers=_AUTH, json=_chat_body("mock-model"))
    assert resp.status_code == 502
    assert resp.json()["error"]["type"] == "upstream_error"
    assert "sk-SECRET-LEAK-CANARY" not in resp.text


def test_list_models_filters_allowlist() -> None:
    with TestClient(_app()) as client:
        resp = client.get("/v1/models", headers=_AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "list"
    ids = {m["id"] for m in data["data"]}
    # 只列出白名单内可路由模型(secret-model 不应出现)。
    assert ids == {"mock-model"}


@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    content=st.text(
        alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=1, max_size=120
    ),
    model=st.sampled_from(["mock-model", "secret-model", "other-model"]),
)
def test_fuzz_never_500(content: str, model: str) -> None:
    with TestClient(_app()) as client:
        resp = client.post(
            "/v1/chat/completions",
            headers=_AUTH,
            json={"model": model, "messages": [{"role": "user", "content": content}]},
        )
    # 任意合法 key + 多样请求下,网关永远返回结构化响应,绝不裸 500。
    assert resp.status_code != 500
    assert resp.status_code in {200, 403}
    assert resp.headers["content-type"].startswith("application/json")
