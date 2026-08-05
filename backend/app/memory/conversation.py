import json
from functools import lru_cache

import redis

from app.config import get_settings


class ConversationMemory:
    """Redis-backed last-N-turns store, so follow-up questions ('what about
    the dissent?') have context. Capped and TTL'd - not a durable chat log."""

    def __init__(self, client: redis.Redis, max_turns: int, ttl_seconds: int) -> None:
        self._client = client
        self._max_turns = max_turns
        self._ttl = ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"memory:{session_id}"

    def load(self, session_id: str) -> str:
        raw_turns = self._client.lrange(self._key(session_id), 0, -1)
        if not raw_turns:
            return ""
        turns = [json.loads(t) for t in raw_turns]
        return "\n".join(f"Q: {t['question']}\nA: {t['answer']}" for t in turns)

    def append(self, session_id: str, question: str, answer: str) -> None:
        key = self._key(session_id)
        pipe = self._client.pipeline()
        pipe.rpush(key, json.dumps({"question": question, "answer": answer}))
        pipe.ltrim(key, -self._max_turns, -1)
        pipe.expire(key, self._ttl)
        pipe.execute()


@lru_cache
def get_conversation_memory() -> ConversationMemory:
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    return ConversationMemory(client, settings.conversation_memory_turns, settings.conversation_memory_ttl_seconds)
