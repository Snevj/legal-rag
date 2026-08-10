from functools import lru_cache

import numpy as np
import redis
from redis.commands.search.field import NumericField, TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from app.config import get_settings

CHUNK_KEY_PREFIX = "chunk:"
KNOWN_TITLES_KEY = "corpus:known_titles"


class RedisVectorStore:
    def __init__(self, redis_url: str, index_name: str, embedding_dim: int) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._index_name = index_name
        self._embedding_dim = embedding_dim
        self._ensure_index()

    def _ensure_index(self) -> None:
        try:
            self._client.ft(self._index_name).info()
            return
        except redis.exceptions.ResponseError:
            pass  # index does not exist yet, create it below

        schema = (
            TagField("doc_id"),
            TextField("source_title"),
            NumericField("chunk_index"),
            TextField("text"),
            VectorField(
                "embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self._embedding_dim,
                    "DISTANCE_METRIC": "COSINE",
                },
            ),
        )
        definition = IndexDefinition(prefix=[CHUNK_KEY_PREFIX], index_type=IndexType.HASH)
        self._client.ft(self._index_name).create_index(fields=schema, definition=definition)

    def upsert_chunks(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        pipe = self._client.pipeline(transaction=False)
        titles: set[str] = set()
        for chunk, vector in zip(chunks, embeddings):
            key = f"{CHUNK_KEY_PREFIX}{chunk['doc_id']}:{chunk['chunk_index']}"
            vector_bytes = np.array(vector, dtype=np.float32).tobytes()
            pipe.hset(
                key,
                mapping={
                    "doc_id": chunk["doc_id"],
                    "source_title": chunk["source_title"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "embedding": vector_bytes,
                },
            )
            titles.add(chunk["source_title"])
        if titles:
            # Corpus-wide registry of every ingested document's title, kept
            # separately from the vector index - this is what lets citation
            # verification check "does this case exist anywhere in the
            # corpus" rather than only "was it retrieved for this query".
            pipe.sadd(KNOWN_TITLES_KEY, *titles)
        pipe.execute()

    def known_titles(self) -> set[str]:
        return self._client.smembers(KNOWN_TITLES_KEY)

    def search(self, query_vector: list[float], top_k: int) -> list[dict]:
        vector_bytes = np.array(query_vector, dtype=np.float32).tobytes()
        query = (
            Query(f"*=>[KNN {top_k} @embedding $vec AS distance]")
            .sort_by("distance")
            .return_fields("doc_id", "source_title", "chunk_index", "text", "distance")
            .dialect(2)
        )
        results = self._client.ft(self._index_name).search(
            query, query_params={"vec": vector_bytes}
        )
        return [
            {
                "doc_id": doc.doc_id,
                "source_title": doc.source_title,
                "chunk_index": int(doc.chunk_index),
                "text": doc.text,
                "distance": float(doc.distance),
            }
            for doc in results.docs
        ]

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except redis.exceptions.RedisError:
            return False


@lru_cache
def get_vector_store() -> RedisVectorStore:
    settings = get_settings()
    return RedisVectorStore(
        redis_url=settings.redis_url,
        index_name=settings.redis_index_name,
        embedding_dim=settings.embedding_dim,
    )
