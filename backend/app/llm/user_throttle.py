import time
from functools import lru_cache

import redis

from app.config import get_settings


class UserThrottle:
    """Fixed-window per-session request cap - tighter than the global model
    buckets, purely to stop one session from hogging the shared quota."""

    def __init__(self, client: redis.Redis, limit_per_minute: int) -> None:
        self._client = client
        self._limit = limit_per_minute

    def check_and_increment(self, session_id: str) -> bool:
        window = int(time.time() // 60)
        key = f"throttle:{session_id}:{window}"
        count = self._client.incr(key)
        if count == 1:
            self._client.expire(key, 60)
        return count <= self._limit


@lru_cache
def get_user_throttle() -> UserThrottle:
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    return UserThrottle(client, settings.per_user_rpm_limit)
