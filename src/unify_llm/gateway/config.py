"""网关配置模型 + YAML 加载器(隐藏 key 的 OpenAI 兼容代理网关)。

网关持有的是**应用 key 的 sha256**(明文从不落盘),与上游各厂商真实 key 完全隔离;模型路由把
对外公开的 model id 映射到"哪个 provider + 哪个上游 model + 计价",真实上游 key 由工厂在服务端
从 env 取,绝不出现在任何网关响应/日志里。
"""

import hashlib
import os
from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

from unify_llm.core.settings import PROJECT_ROOT


class AppKey(BaseModel):
    """一个被授权的应用 key(只存 sha256,明文从不存储)。

    Attributes:
        app_id: 应用标识(用于限流/预算分桶与日志,非机密)。
        key_sha256: 明文应用 key 的小写十六进制 sha256;鉴权时常数时间比对。
        allowed_models: 该应用可路由的公开 model id 列表;单个 ``"*"`` 表示放行全部可路由模型。
        rate_limit_rpm: 每分钟请求数上限(令牌桶容量)。
        rate_limit_tpm: 每分钟 token 上限(令牌桶容量)。
        budget_usd: 每个预算窗口的花费上限(美元);None 表示不限。
    """

    app_id: str
    key_sha256: str
    allowed_models: list[str] = Field(default_factory=list)
    rate_limit_rpm: int = 60
    rate_limit_tpm: int = 100_000
    budget_usd: float | None = None


class ModelRoute(BaseModel):
    """一条公开 model id → 上游 provider/model 的路由(含计价)。

    Attributes:
        provider: 工厂注册表里的 provider 名(openai / anthropic / ... / mock)。
        upstream_model: 实际发给上游的 model 名(对客户端隐藏)。
        input_price_per_1k: 每千输入 token 的计价(美元),用于预算扣减。
        output_price_per_1k: 每千输出 token 的计价(美元)。
    """

    provider: str
    upstream_model: str
    input_price_per_1k: float = 0.0
    output_price_per_1k: float = 0.0


class GatewayConfig(BaseModel):
    """网关的全部配置(应用 key 表 + 模型路由表 + 限流/预算/后端)。

    Attributes:
        app_keys: 被授权的应用 key(仅 sha256)。
        models: 公开 model id → 路由。
        budget_window_seconds: 预算窗口长度(秒,固定窗口)。
        backend: 限流/预算后端;``memory``(默认,单进程)或 ``redis``(水平扩展)。
        redis_url: redis 后端连接串(backend==redis 时必填)。
    """

    app_keys: list[AppKey] = Field(default_factory=list)
    models: dict[str, ModelRoute] = Field(default_factory=dict)
    budget_window_seconds: int = 86_400
    backend: Literal["memory", "redis"] = "memory"
    redis_url: str | None = None


def hash_app_key(plaintext: str) -> str:
    """明文应用 key → 小写十六进制 sha256(配置只存该摘要,明文从不落盘)。"""
    return hashlib.sha256(plaintext.encode()).hexdigest()


def _default_config_path() -> Path:
    """默认配置路径:``APP_GATEWAY_CONFIG`` 环境变量优先,否则 configs/gateway.yaml。"""
    override = os.getenv("APP_GATEWAY_CONFIG")
    if override:
        return Path(override)
    return PROJECT_ROOT / "configs" / "gateway.yaml"


def load_gateway_config(path: Path | None = None) -> GatewayConfig:
    """从 YAML 读取网关配置;文件不存在则返回最小内置默认(空 key/空路由)。

    测试一律在代码里直接构造 GatewayConfig 注入,本函数仅供从磁盘启动时使用,故不缓存。
    """
    cfg_path = path if path is not None else _default_config_path()
    if not cfg_path.is_file():
        return GatewayConfig()
    with cfg_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        return GatewayConfig()
    return GatewayConfig.model_validate(raw)
