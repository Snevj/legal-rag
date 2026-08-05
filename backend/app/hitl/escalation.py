import json
import time
import uuid
from functools import lru_cache

import redis

from app.config import get_settings

QUEUE_KEY = "escalations:pending"
ITEM_KEY_PREFIX = "escalation:"


class EscalationQueue:
    """Redis-backed human-review queue. No auth/reviewer-identity system yet
    (see RED_TEAMING.md) - this just makes flagged responses visible and
    resolvable, it doesn't gate them from being shown to the user."""

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    def add(self, session_id: str, question: str, answer: str, reasons: list[str]) -> str:
        escalation_id = uuid.uuid4().hex
        record = {
            "id": escalation_id,
            "session_id": session_id,
            "question": question,
            "answer": answer,
            "reasons": reasons,
            "created_at": time.time(),
            "status": "pending",
        }
        pipe = self._client.pipeline()
        pipe.set(f"{ITEM_KEY_PREFIX}{escalation_id}", json.dumps(record))
        pipe.rpush(QUEUE_KEY, escalation_id)
        pipe.execute()
        return escalation_id

    def list_pending(self) -> list[dict]:
        ids = self._client.lrange(QUEUE_KEY, 0, -1)
        records = []
        for escalation_id in ids:
            raw = self._client.get(f"{ITEM_KEY_PREFIX}{escalation_id}")
            if raw:
                record = json.loads(raw)
                if record["status"] == "pending":
                    records.append(record)
        return records

    def resolve(self, escalation_id: str, notes: str = "") -> dict | None:
        key = f"{ITEM_KEY_PREFIX}{escalation_id}"
        raw = self._client.get(key)
        if raw is None:
            return None
        record = json.loads(raw)
        record["status"] = "resolved"
        record["resolution_notes"] = notes
        record["resolved_at"] = time.time()
        self._client.set(key, json.dumps(record))
        self._client.lrem(QUEUE_KEY, 0, escalation_id)
        return record


@lru_cache
def get_escalation_queue() -> EscalationQueue:
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    return EscalationQueue(client)
