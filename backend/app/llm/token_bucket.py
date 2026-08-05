import time
from functools import lru_cache

import redis

from app.config import get_settings

# Classic token-bucket: tokens refill continuously at `refill_rate_per_second`,
# capped at `capacity`. Atomic via Lua so concurrent requests can't race past
# the limit between a GET and a SET.
_BUCKET_SCRIPT = """
local bucket = redis.call('HMGET', KEYS[1], 'tokens', 'ts')
local tokens = tonumber(bucket[1])
local ts = tonumber(bucket[2])
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

if tokens == nil then
  tokens = capacity
  ts = now
end

local elapsed = math.max(0, now - ts)
tokens = math.min(capacity, tokens + elapsed * refill_rate)

local allowed = 0
if tokens >= cost then
  tokens = tokens - cost
  allowed = 1
end

redis.call('HMSET', KEYS[1], 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', KEYS[1], 3600)
return allowed
"""


class RedisTokenBucket:
    def __init__(self, client: redis.Redis, key: str, capacity: float, refill_rate_per_second: float) -> None:
        self._client = client
        self._key = key
        self.capacity = capacity
        self._refill_rate = refill_rate_per_second
        self._script = client.register_script(_BUCKET_SCRIPT)

    def try_consume(self, cost: float = 1.0) -> bool:
        allowed = self._script(keys=[self._key], args=[self.capacity, self._refill_rate, cost, time.time()])
        return bool(int(allowed))

    def refund(self, cost: float) -> None:
        self._client.hincrbyfloat(self._key, "tokens", cost)


class DualTokenBucket:
    """Enforces both RPM and TPM for one model. A request must have capacity
    in both buckets; if the TPM check fails after RPM already succeeded, the
    RPM token is refunded so it isn't wasted."""

    def __init__(self, client: redis.Redis, model: str, rpm_limit: int, tpm_limit: int) -> None:
        self.tpm_capacity = tpm_limit
        self._rpm = RedisTokenBucket(client, f"bucket:rpm:{model}", capacity=rpm_limit, refill_rate_per_second=rpm_limit / 60)
        self._tpm = RedisTokenBucket(client, f"bucket:tpm:{model}", capacity=tpm_limit, refill_rate_per_second=tpm_limit / 60)

    def try_consume(self, estimated_tokens: int) -> bool:
        if not self._rpm.try_consume(1):
            return False
        if not self._tpm.try_consume(estimated_tokens):
            self._rpm.refund(1)
            return False
        return True


@lru_cache
def get_model_buckets() -> dict[str, DualTokenBucket]:
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    return {
        settings.groq_model_cheap: DualTokenBucket(
            client, settings.groq_model_cheap, settings.rpm_limit_cheap, settings.tpm_limit_cheap
        ),
        settings.groq_model_expensive: DualTokenBucket(
            client, settings.groq_model_expensive, settings.rpm_limit_expensive, settings.tpm_limit_expensive
        ),
    }
