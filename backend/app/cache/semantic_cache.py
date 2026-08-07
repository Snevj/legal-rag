import json
import time
from functools import lru_cache

import numpy as np
import redis
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from app.config import get_settings

CACHE_KEY_PREFIX = "qacache:"


class SemanticCache:
    """Near-duplicate question cache: embeds the question, KNN-searches a
    dedicated Redis vector index for a prior question above the similarity
    threshold, and returns its full cached response - skipping retrieve/
    rerank/generate (and their cost) entirely on a hit."""

    def __init__(
        self,
        client: redis.Redis,
        index_name: str,
        embedding_dim: int,
        similarity_threshold: float,
        ttl_seconds: int,
    ) -> None:
        self._client = client
        self._index_name = index_name
        self._embedding_dim = embedding_dim
        self._similarity_threshold = similarity_threshold
        self._ttl = ttl_seconds
        self._ensure_index()

    def _ensure_index(self) -> None:
        try:
            self._client.ft(self._index_name).info()
            return
        except redis.exceptions.ResponseError:
            pass

        schema = (
            TextField("question"),
            TextField("response_json"),
            VectorField(
                "embedding",
                "HNSW",
                {"TYPE": "FLOAT32", "DIM": self._embedding_dim, "DISTANCE_METRIC": "COSINE"},
            ),
        )
        definition = IndexDefinition(prefix=[CACHE_KEY_PREFIX], index_type=IndexType.HASH)
        self._client.ft(self._index_name).create_index(fields=schema, definition=definition)

    def lookup(self, query_vector: list[float]) -> dict | None:
        vector_bytes = np.array(query_vector, dtype=np.float32).tobytes()
        query = (
            Query("*=>[KNN 1 @embedding $vec AS distance]")
            .sort_by("distance")
            .return_fields("response_json", "distance")
            .dialect(2)
        )
        results = self._client.ft(self._index_name).search(query, query_params={"vec": vector_bytes})
        if not results.docs:
            return None

        doc = results.docs[0]
        similarity = 1 - float(doc.distance)  # COSINE distance = 1 - cosine_similarity
        if similarity < self._similarity_threshold:
            return None
        return json.loads(doc.response_json)

    def store(self, query_vector: list[float], question: str, payload: dict) -> None:
        key = f"{CACHE_KEY_PREFIX}{abs(hash(question))}_{int(time.time() * 1000)}"
        vector_bytes = np.array(query_vector, dtype=np.float32).tobytes()
        self._client.hset(
            key,
            mapping={"question": question, "response_json": json.dumps(payload), "embedding": vector_bytes},
        )
        self._client.expire(key, self._ttl)
        return key

    def clear_all(self) -> None:
        """Delete all cache entries with the configured prefix. Useful for tests."""
        cursor = "0"
        pattern = f"{CACHE_KEY_PREFIX}*"
        # Use SCAN to avoid blocking Redis
        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=1000)
            if keys:
                self._client.delete(*keys)
            if cursor == "0":
                break


@lru_cache
def get_semantic_cache() -> SemanticCache:
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    return SemanticCache(
        client,
        settings.redis_cache_index_name,
        settings.embedding_dim,
        settings.semantic_cache_similarity_threshold,
        settings.semantic_cache_ttl_seconds,
    )


def clear_semantic_cache() -> None:
    """Convenience helper to clear all semantic cache keys (for tests)."""
    get_semantic_cache().clear_all()
