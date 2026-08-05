import time
from functools import lru_cache

import redis

from app.config import get_settings


class CircuitBreaker:
    """Per-model breaker: opens after `failure_threshold` consecutive failures,
    fails fast (no calls to the provider) for `cooldown_seconds`, then allows a
    single half-open trial request."""

    def __init__(self, client: redis.Redis, model: str, failure_threshold: int, cooldown_seconds: int) -> None:
        self._client = client
        self._failures_key = f"breaker:{model}:failures"
        self._open_until_key = f"breaker:{model}:open_until"
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds

    def is_open(self) -> bool:
        open_until = self._client.get(self._open_until_key)
        if open_until is None:
            return False
        if time.time() >= float(open_until):
            # Cooldown elapsed - clear the marker and let one half-open trial through.
            self._client.delete(self._open_until_key)
            return False
        return True

    def record_success(self) -> None:
        self._client.delete(self._failures_key)
        self._client.delete(self._open_until_key)

    def record_failure(self) -> None:
        failures = self._client.incr(self._failures_key)
        self._client.expire(self._failures_key, self._cooldown * 4)
        if failures >= self._threshold:
            self._client.set(self._open_until_key, time.time() + self._cooldown)


@lru_cache
def get_circuit_breakers() -> dict[str, CircuitBreaker]:
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    return {
        settings.groq_model_cheap: CircuitBreaker(
            client,
            settings.groq_model_cheap,
            settings.circuit_breaker_failure_threshold,
            settings.circuit_breaker_cooldown_seconds,
        ),
        settings.groq_model_expensive: CircuitBreaker(
            client,
            settings.groq_model_expensive,
            settings.circuit_breaker_failure_threshold,
            settings.circuit_breaker_cooldown_seconds,
        ),
    }
