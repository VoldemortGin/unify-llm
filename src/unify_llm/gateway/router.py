"""公开 model id → 上游 provider 路由 + 每应用模型白名单校验。

真实上游 provider key 由工厂在服务端从 env 取,绝不出现在任何网关响应/日志里;本模块只决定
"这个公开 model 走哪个 provider/上游 model"以及"这个应用能不能用这个 model"。
"""

from unify_llm.core.exceptions import ModelNotFoundError
from unify_llm.gateway.auth import AuthContext
from unify_llm.gateway.config import GatewayConfig, ModelRoute
from unify_llm.gateway.errors import ModelNotAllowedError


def resolve_route(model: str, config: GatewayConfig) -> ModelRoute:
    """查公开 model 的路由;不存在 → ModelNotFoundError(404)。"""
    route = config.models.get(model)
    if route is None:
        raise ModelNotFoundError(model)
    return route


def check_model_allowed(model: str, auth: AuthContext) -> None:
    """校验应用是否被授权使用该 model;否则 ModelNotAllowedError(403)。"""
    if "*" in auth.allowed_models or model in auth.allowed_models:
        return
    raise ModelNotAllowedError(f"Model '{model}' is not permitted for this application")
