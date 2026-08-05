import datetime
from functools import lru_cache

import redis

from app.config import get_settings


class BudgetExceededError(Exception):
    def __init__(self, scope: str, limit: int, used: int) -> None:
        self.scope = scope
        self.limit = limit
        self.used = used
        super().__init__(f"{scope} daily token budget exceeded: {used}/{limit} tokens used today")


def _today() -> str:
    return datetime.date.today().isoformat()


class BudgetTracker:
    """Redis-backed cumulative token/cost counters, checked pre-flight against
    the estimate (so a request that would blow the budget is rejected before
    any Groq call is made) and reconciled post-call with actual usage."""

    def __init__(self, client: redis.Redis, global_daily_limit: int, session_daily_limit: int) -> None:
        self._client = client
        self._global_limit = global_daily_limit
        self._session_limit = session_daily_limit

    def _global_key(self) -> str:
        return f"usage:global:{_today()}"

    def _session_key(self, session_id: str) -> str:
        return f"usage:session:{session_id}:{_today()}"

    def check_preflight(self, session_id: str, estimated_tokens: int) -> None:
        global_used = int(self._client.hget(self._global_key(), "tokens") or 0)
        if global_used + estimated_tokens > self._global_limit:
            raise BudgetExceededError("global", self._global_limit, global_used)

        session_used = int(self._client.hget(self._session_key(session_id), "tokens") or 0)
        if session_used + estimated_tokens > self._session_limit:
            raise BudgetExceededError("session", self._session_limit, session_used)

    def record_usage(self, session_id: str, tokens_used: int, cost_usd: float) -> None:
        pipe = self._client.pipeline()
        for key in (self._global_key(), self._session_key(session_id)):
            pipe.hincrby(key, "tokens", tokens_used)
            pipe.hincrbyfloat(key, "cost_usd", cost_usd)
            pipe.expire(key, 172_800)  # 2 days, comfortably covers the "today" window
        pipe.execute()

    def get_usage(self, session_id: str | None = None) -> dict:
        g = self._client.hgetall(self._global_key())
        result = {
            "date": _today(),
            "global_tokens_used": int(g.get("tokens", 0)),
            "global_cost_usd": round(float(g.get("cost_usd", 0.0)), 6),
            "global_token_budget": self._global_limit,
        }
        if session_id:
            s = self._client.hgetall(self._session_key(session_id))
            result["session_tokens_used"] = int(s.get("tokens", 0))
            result["session_cost_usd"] = round(float(s.get("cost_usd", 0.0)), 6)
            result["session_token_budget"] = self._session_limit
        return result


@lru_cache
def get_budget_tracker() -> BudgetTracker:
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    return BudgetTracker(client, settings.daily_token_budget_global, settings.daily_token_budget_per_session)
