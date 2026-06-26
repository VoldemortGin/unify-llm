"""FastAPI 隐藏 key 代理网关:鉴权 → 路由 → 限流/预算 → 上游(ADR-09/10)。

对外是 OpenAI 兼容的 ``/v1/chat/completions`` 与 ``/v1/models``;客户端只持有网关应用 key,真实
上游厂商 key 由工厂在服务端从 env 取,绝不出现在任何响应/日志里。进程级共享一个 ``httpx.AsyncClient``
(lifespan 创建/关闭,ADR-10),按 provider 缓存复用 provider 实例。
"""

import contextlib
import json
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from unify_llm.gateway.auth import AuthContext, require_auth
from unify_llm.gateway.config import GatewayConfig, ModelRoute, load_gateway_config
from unify_llm.gateway.errors import register_exception_handlers
from unify_llm.gateway.ratelimit import RateLimiter, build_backend
from unify_llm.gateway.router import check_model_allowed, resolve_route
from unify_llm.models import ChatRequest, MessageDelta, StreamChunk
from unify_llm.ports.factory import make_llm
from unify_llm.ports.llm import LLMProvider
from unify_llm.utils import estimate_tokens

# 给定 provider 名 + 共享异步客户端,产出一个满足 LLMProvider 的实现(可注入,测试用 Mock 替换)。
ProviderFactory = Callable[[str, httpx.AsyncClient], LLMProvider]


def _default_provider_factory(name: str, client: httpx.AsyncClient) -> LLMProvider:
    """默认 provider 工厂:经唯一装配缝 ``make_llm`` 注入进程级共享异步客户端。"""
    return make_llm(name, http_client=client)


def _compute_cost(route: ModelRoute, prompt_tokens: int, completion_tokens: int) -> float:
    """按路由计价算本次花费(美元)。"""
    return (prompt_tokens / 1000.0) * route.input_price_per_1k + (
        completion_tokens / 1000.0
    ) * route.output_price_per_1k


def _delta_dict(delta: MessageDelta) -> dict[str, object]:
    """流式 delta → OpenAI chunk 的 delta 体(只含 role/content,枚举转纯串)。"""
    out: dict[str, object] = {}
    if delta.role is not None:
        out["role"] = delta.role.value
    if delta.content is not None:
        out["content"] = delta.content
    return out


def _stream_event(chunk: StreamChunk, public_model: str) -> dict[str, object]:
    """统一 StreamChunk → OpenAI ``chat.completion.chunk`` 体(model 还原为公开 id)。"""
    return {
        "id": chunk.id,
        "object": "chat.completion.chunk",
        "created": chunk.created,
        "model": public_model,
        "choices": [
            {
                "index": d.index,
                "delta": _delta_dict(d.delta),
                "finish_reason": d.finish_reason.value if d.finish_reason is not None else None,
            }
            for d in chunk.choices
        ],
    }


def create_app(
    config: GatewayConfig | None = None,
    *,
    make_provider: ProviderFactory | None = None,
) -> FastAPI:
    """组装网关 FastAPI 应用。

    Args:
        config: 网关配置(应用 key 表 + 路由表 + 限流/预算);None 时用空默认(随后显式注入)。
        make_provider: 注入的 provider 工厂(测试用 Mock);None 时用经 ``make_llm`` 的默认工厂。
    """
    gateway_config = config if config is not None else GatewayConfig()
    provider_factory: ProviderFactory = (
        make_provider if make_provider is not None else _default_provider_factory
    )
    rate_limiter = RateLimiter(build_backend(gateway_config), gateway_config.budget_window_seconds)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # 启动:建一个进程级共享异步客户端(ADR-10);关停:关它 + 关缓存 provider 的同步客户端。
        timeout = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)
        limits = httpx.Limits(
            max_keepalive_connections=20, max_connections=100, keepalive_expiry=30.0
        )
        app.state.http_client = httpx.AsyncClient(timeout=timeout, limits=limits)
        try:
            yield
        finally:
            await app.state.http_client.aclose()
            for provider in app.state.provider_cache.values():
                close = getattr(provider, "close", None)
                if callable(close):
                    with contextlib.suppress(Exception):
                        close()

    app = FastAPI(title="unify-llm gateway", lifespan=lifespan)
    app.state.gateway_config = gateway_config
    app.state.rate_limiter = rate_limiter
    app.state.make_provider = provider_factory
    app.state.provider_cache = {}

    register_exception_handlers(app)

    def _get_provider(request: Request, provider_name: str) -> LLMProvider:
        """按 provider 名取缓存 provider,未命中则用注入的工厂建并缓存。"""
        cache: dict[str, LLMProvider] = request.app.state.provider_cache
        provider = cache.get(provider_name)
        if provider is None:
            factory_fn: ProviderFactory = request.app.state.make_provider
            provider = factory_fn(provider_name, request.app.state.http_client)
            cache[provider_name] = provider
        return provider

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/models")
    async def list_models(
        auth: Annotated[AuthContext, Depends(require_auth)],
    ) -> dict[str, object]:
        allow_all = "*" in auth.allowed_models
        data: list[dict[str, object]] = [
            {"id": model_id, "object": "model", "owned_by": "unify-llm"}
            for model_id in gateway_config.models
            if allow_all or model_id in auth.allowed_models
        ]
        return {"object": "list", "data": data}

    @app.post("/v1/chat/completions")
    async def chat_completions(
        req: ChatRequest,
        request: Request,
        auth: Annotated[AuthContext, Depends(require_auth)],
    ) -> Response:
        check_model_allowed(req.model, auth)
        route = resolve_route(req.model, gateway_config)
        await rate_limiter.check_request(auth)
        provider = _get_provider(request, route.provider)
        # 把对外的公开 model 重写成上游真实 model(对客户端隐藏)。
        upstream_req = req.model_copy(update={"model": route.upstream_model})

        if req.stream:

            async def event_stream() -> AsyncIterator[str]:
                accumulated: list[str] = []
                async for chunk in provider.achat_stream(upstream_req):
                    if chunk.content:
                        accumulated.append(chunk.content)
                    yield f"data: {json.dumps(_stream_event(chunk, req.model))}\n\n"
                # 流式预算/TPM:用累计文本估算 token,尽力而为地在收尾时计费。
                tokens = estimate_tokens("".join(accumulated))
                await rate_limiter.record_usage(auth, tokens, _compute_cost(route, 0, tokens))
                yield "data: [DONE]\n\n"

            return StreamingResponse(event_stream(), media_type="text/event-stream")

        resp = await provider.achat(upstream_req)
        usage = resp.usage
        prompt_tokens = usage.prompt_tokens if usage is not None else 0
        completion_tokens = usage.completion_tokens if usage is not None else 0
        total_tokens = usage.total_tokens if usage is not None else 0
        cost = _compute_cost(route, prompt_tokens, completion_tokens)
        await rate_limiter.record_usage(auth, total_tokens, cost)

        # OpenAI 兼容序列化:还原公开 model id、丢弃内部 raw_response、补 object 字段。
        body = resp.model_dump(mode="json", exclude={"raw_response"})
        body["model"] = req.model
        body["object"] = "chat.completion"
        return JSONResponse(content=body)

    return app


def _build_default_app() -> FastAPI:
    """容器/生产入口用的默认应用,供 ``uvicorn unify_llm.gateway.app:app`` 直接拉起。

    配置全走 env(机密不进镜像):
    - 应用 key 表 + 模型路由从 YAML 加载(``APP_GATEWAY_CONFIG`` 指向挂载的 gateway.yaml,
      缺省 ``configs/gateway.yaml``;仅 sha256,非机密);
    - 限流/预算后端由 ``APP_RATELIMIT_BACKEND`` / ``APP_REDIS_URL`` 覆盖(水平扩容时设 redis)。

    上游真实厂商 key 仍由工厂在请求期各自从 env 取,绝不进配置文件,也绝不出网关响应/日志。
    """
    config = load_gateway_config()
    overrides: dict[str, object] = {}
    backend = os.getenv("APP_RATELIMIT_BACKEND")
    if backend:
        overrides["backend"] = backend
    redis_url = os.getenv("APP_REDIS_URL")
    if redis_url:
        overrides["redis_url"] = redis_url
    if overrides:
        config = config.model_copy(update=overrides)
    return create_app(config)


# 模块级默认应用:env/yaml 驱动(供 ``uvicorn unify_llm.gateway.app:app`` 直接拉起)。
app = _build_default_app()
