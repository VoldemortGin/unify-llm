"""Redis 限流/预算后端(水平扩展)。仅在选用 redis 后端时被 ``build_backend`` 惰性导入。

令牌桶用一段 Lua 脚本原子地"补充+消费",预算窗口用 ``INCRBYFLOAT`` + ``EXPIRE`` 实现固定窗口。
本文件受 ``mypy src`` 严格类型检查(dev 装了 redis-py,自带类型提示),但测试从不导入它,也从不连
真 Redis;redis-py 异步命令返回 ``Awaitable[Any]``,故对结果一律用显式 ``int(...)``/``float(...)``
归一,而非整段 ``# type: ignore``。
"""

import time
from typing import cast

import redis.asyncio as aioredis

# 原子令牌桶:KEYS[1]=桶 key;ARGV=capacity, refill_per_sec, cost, now。
# 返回 {allowed(0/1), tostring(retry_after_seconds)}。
_TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])
local now = tonumber(ARGV[4])
local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts = tonumber(data[2])
if tokens == nil then
  tokens = capacity
  ts = now
end
tokens = math.min(capacity, tokens + (now - ts) * refill)
local allowed = 0
local retry_after = 0
if tokens >= cost then
  tokens = tokens - cost
  allowed = 1
elseif refill > 0 then
  retry_after = (cost - tokens) / refill
else
  retry_after = 86400
end
redis.call('HSET', key, 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', key, 86400)
return {allowed, tostring(retry_after)}
"""


class RedisRateLimitBackend:
    """分布式令牌桶 + 固定窗口花费(Redis Lua 原子消费 + INCRBYFLOAT/EXPIRE)。"""

    def __init__(self, redis_url: str) -> None:
        self._redis: aioredis.Redis = aioredis.from_url(redis_url, decode_responses=True)
        self._token_script = self._redis.register_script(_TOKEN_BUCKET_LUA)

    async def take_token(
        self, key: str, capacity: float, refill_per_sec: float, cost: float
    ) -> tuple[bool, float]:
        now = time.time()
        raw = await self._token_script(
            keys=[f"bucket:{key}"],
            args=[capacity, refill_per_sec, cost, now],
        )
        result = cast("list[object]", raw)
        allowed = int(cast("int | str", result[0])) == 1
        retry_after = float(cast("int | str | float", result[1]))
        return allowed, retry_after

    async def add_spend(
        self, key: str, window_seconds: int, amount_usd: float
    ) -> tuple[float, float]:
        spend_key = f"spend:{key}"
        total = float(await self._redis.incrbyfloat(spend_key, amount_usd))
        ttl = int(await self._redis.ttl(spend_key))
        if ttl < 0:
            await self._redis.expire(spend_key, window_seconds)
            ttl = window_seconds
        return total, float(ttl)
