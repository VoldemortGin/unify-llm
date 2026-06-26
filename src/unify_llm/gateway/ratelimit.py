"""每应用 key 的令牌桶限流 + 预算计费(默认内存后端,可选 Redis 水平扩展)。

后端抽象成 ``RateLimitBackend`` Protocol(令牌桶 + 固定窗口花费),默认 ``InMemoryRateLimitBackend``
(确定性、无外部依赖);Redis 实现单独放在 ``ratelimit_redis`` 模块,仅在选用 redis 后端时才惰性
导入,故本模块导入永不要求装 redis。
"""

import asyncio
import time
from math import ceil
from typing import Protocol, runtime_checkable

from unify_llm.core.exceptions import RateLimitError
from unify_llm.gateway.auth import AuthContext
from unify_llm.gateway.config import GatewayConfig


@runtime_checkable
class RateLimitBackend(Protocol):
    """限流/预算状态后端(内存或 Redis);async 以便 Redis 实现走异步 I/O。"""

    async def take_token(
        self, key: str, capacity: float, refill_per_sec: float, cost: float
    ) -> tuple[bool, float]:
        """令牌桶:尝试从桶 ``key`` 消费 ``cost`` 个令牌;返回 (是否放行, 建议重试秒数)。"""
        ...

    async def add_spend(
        self, key: str, window_seconds: int, amount_usd: float
    ) -> tuple[float, float]:
        """固定窗口累加花费;返回 (当前窗口内累计花费, 距窗口重置的剩余秒数)。"""
        ...


class InMemoryRateLimitBackend:
    """单进程内存后端:令牌桶 + 固定窗口花费,均由一把 asyncio.Lock 串行化(确定性)。"""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        # key -> (tokens, last_refill_monotonic)
        self._buckets: dict[str, tuple[float, float]] = {}
        # key -> (total_spend, window_start_monotonic)
        self._spend: dict[str, tuple[float, float]] = {}

    async def take_token(
        self, key: str, capacity: float, refill_per_sec: float, cost: float
    ) -> tuple[bool, float]:
        async with self._lock:
            now = time.monotonic()
            tokens, last = self._buckets.get(key, (capacity, now))
            tokens = min(capacity, tokens + (now - last) * refill_per_sec)
            if tokens >= cost:
                self._buckets[key] = (tokens - cost, now)
                return True, 0.0
            self._buckets[key] = (tokens, now)
            deficit = cost - tokens
            retry_after = deficit / refill_per_sec if refill_per_sec > 0 else 86_400.0
            return False, retry_after

    async def add_spend(
        self, key: str, window_seconds: int, amount_usd: float
    ) -> tuple[float, float]:
        async with self._lock:
            now = time.monotonic()
            total, start = self._spend.get(key, (0.0, now))
            if now - start >= window_seconds:
                total, start = 0.0, now
            total += amount_usd
            self._spend[key] = (total, start)
            seconds_until_reset = max(0.0, window_seconds - (now - start))
            return total, seconds_until_reset


class RateLimiter:
    """限流编排器:请求前消费 RPM 桶 + 校验预算,响应后消费 TPM 桶 + 计入花费。"""

    def __init__(self, backend: RateLimitBackend, budget_window_seconds: int) -> None:
        self._backend = backend
        self._budget_window_seconds = budget_window_seconds

    async def check_request(self, auth: AuthContext) -> None:
        """放行前:消费 1 个 RPM 令牌;预算已超则拒。"""
        allowed, retry_after = await self._backend.take_token(
            f"req:{auth.app_id}",
            capacity=float(auth.rate_limit_rpm),
            refill_per_sec=auth.rate_limit_rpm / 60.0,
            cost=1.0,
        )
        if not allowed:
            raise RateLimitError("Request rate limit exceeded", retry_after=ceil(retry_after))

        if auth.budget_usd is not None:
            # peek 当前窗口花费(加 0):已达预算即拒。
            spent, seconds_until_reset = await self._backend.add_spend(
                f"budget:{auth.app_id}", self._budget_window_seconds, 0.0
            )
            if spent >= auth.budget_usd:
                raise RateLimitError("Budget exceeded", retry_after=ceil(seconds_until_reset))

    async def record_usage(self, auth: AuthContext, total_tokens: int, cost_usd: float) -> None:
        """响应后:消费 TPM 令牌(超用只影响下次请求,不中途拒)+ 计入预算花费。"""
        await self._backend.take_token(
            f"tok:{auth.app_id}",
            capacity=float(auth.rate_limit_tpm),
            refill_per_sec=auth.rate_limit_tpm / 60.0,
            cost=float(total_tokens),
        )
        if auth.budget_usd is not None:
            await self._backend.add_spend(
                f"budget:{auth.app_id}", self._budget_window_seconds, cost_usd
            )


def build_backend(config: GatewayConfig) -> RateLimitBackend:
    """按配置造后端:memory → 内存;redis → 惰性导入 Redis 实现(导入本模块永不需要 redis)。"""
    if config.backend == "redis":
        from unify_llm.gateway.ratelimit_redis import RedisRateLimitBackend

        if config.redis_url is None:
            raise ValueError("redis backend requires 'redis_url' in GatewayConfig")
        return RedisRateLimitBackend(config.redis_url)
    return InMemoryRateLimitBackend()
