import json
import time
from functools import lru_cache

import redis

from app.config import get_settings


class ChatHistory:
    """Redis-backed *full* per-turn history (question + the complete
    QueryResponse payload: sources, guardrails, cost, everything), separate
    from ConversationMemory - that module stores only a flattened Q/A string
    sized for LLM prompt context. This one exists purely so the frontend can
    rehydrate the chat UI (GET /history) after a reload or a route change,
    instead of losing every message the moment the chat page unmounts."""

    def __init__(self, client: redis.Redis, max_turns: int, ttl_seconds: int) -> None:
        self._client = client
        self._max_turns = max_turns
        self._ttl = ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"chat_history:{session_id}"

    def append(self, session_id: str, question: str, response: dict) -> None:
        key = self._key(session_id)
        record = {"question": question, "response": response, "asked_at": time.time()}
        pipe = self._client.pipeline()
        pipe.rpush(key, json.dumps(record))
        pipe.ltrim(key, -self._max_turns, -1)
        pipe.expire(key, self._ttl)
        pipe.execute()

    def load(self, session_id: str) -> list[dict]:
        raw_turns = self._client.lrange(self._key(session_id), 0, -1)
        return [json.loads(t) for t in raw_turns]


@lru_cache
def get_chat_history() -> ChatHistory:
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    return ChatHistory(client, settings.chat_history_max_turns, settings.conversation_memory_ttl_seconds)
