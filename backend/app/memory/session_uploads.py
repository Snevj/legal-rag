import json
from functools import lru_cache

import redis

from app.config import get_settings


class SessionUploads:
    """Redis-backed 'last document this session uploaded' pointer. Exists so
    a vague follow-up like 'what is this file about' has something to
    resolve "this file" to - retrieve_node uses it to guarantee the
    just-uploaded document a fair shot at being reranked alongside the
    corpus-wide search, since with a large corpus a single small upload can
    otherwise be crowded out of the top-k entirely. TTL matches conversation
    memory - not meant to be a durable per-user document library."""

    def __init__(self, client: redis.Redis, ttl_seconds: int) -> None:
        self._client = client
        self._ttl = ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"session_upload:{session_id}"

    def record(self, session_id: str, doc_id: str, source_title: str) -> None:
        self._client.set(
            self._key(session_id),
            json.dumps({"doc_id": doc_id, "source_title": source_title}),
            ex=self._ttl,
        )

    def get(self, session_id: str) -> dict | None:
        raw = self._client.get(self._key(session_id))
        return json.loads(raw) if raw else None


@lru_cache
def get_session_uploads() -> SessionUploads:
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    return SessionUploads(client, settings.conversation_memory_ttl_seconds)
