"""Bearer 应用 key 鉴权(与上游各厂商真实 key 完全隔离)。

网关持有的是应用 key 的 sha256 表,与"调上游用哪个真实 key"是两回事:客户端拿应用 key 进来,
网关验通过后在服务端另取上游 key。比对用 ``hmac.compare_digest`` 常数时间,且遍历所有 key(不在
首个不匹配处提前返回)以避免按位置泄露时序信息。
"""

import hmac

from fastapi import Request
from pydantic import BaseModel, Field

from unify_llm.core.exceptions import AuthenticationError
from unify_llm.gateway.config import AppKey, GatewayConfig, hash_app_key


class AuthContext(BaseModel):
    """鉴权通过后携带的应用上下文(限流/预算/可用模型,均非机密)。"""

    app_id: str
    allowed_models: list[str] = Field(default_factory=list)
    rate_limit_rpm: int
    rate_limit_tpm: int
    budget_usd: float | None = None


def _context_from_key(key: AppKey) -> AuthContext:
    """从匹配到的 AppKey 构造 AuthContext。"""
    return AuthContext(
        app_id=key.app_id,
        allowed_models=key.allowed_models,
        rate_limit_rpm=key.rate_limit_rpm,
        rate_limit_tpm=key.rate_limit_tpm,
        budget_usd=key.budget_usd,
    )


def authenticate(authorization: str | None, config: GatewayConfig) -> AuthContext:
    """解析 ``Authorization: Bearer <app_key>`` 并常数时间比对 sha256。

    缺失/格式错 → AuthenticationError("Missing or invalid Authorization header");
    无匹配 → AuthenticationError("Invalid API key")。
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid Authorization header")
    presented = authorization[len("Bearer ") :].strip()
    if not presented:
        raise AuthenticationError("Missing or invalid Authorization header")

    presented_hash = hash_app_key(presented)
    matched: AppKey | None = None
    for key in config.app_keys:
        # 遍历全部 key 累积匹配,不提前 return,避免按匹配位置泄露时序。
        if hmac.compare_digest(presented_hash, key.key_sha256):
            matched = key
    if matched is None:
        raise AuthenticationError("Invalid API key")
    return _context_from_key(matched)


def require_auth(request: Request) -> AuthContext:
    """FastAPI 依赖:从请求头 + ``app.state.gateway_config`` 鉴权。"""
    authorization = request.headers.get("Authorization")
    config: GatewayConfig = request.app.state.gateway_config
    return authenticate(authorization, config)
