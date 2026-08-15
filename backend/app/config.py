from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str
    # Both llama-3.1-8b-instant and llama-3.3-70b-versatile are decommissioned
    # by Groq on 2026-08-16; migrated both to their recommended gpt-oss
    # replacements. Note the free-tier ceilings converge as a result -
    # gpt-oss-20b and gpt-oss-120b both sit at RPD 1,000 / TPM 8,000 /
    # TPD 200K (down from the old models' much larger, and different-sized,
    # ceilings) - re-check console.groq.com/settings/limits before assuming
    # headroom on either tier.
    groq_model_cheap: str = "openai/gpt-oss-20b"
    groq_model_expensive: str = "openai/gpt-oss-120b"

    # Free-tier limits per Groq's published docs (console.groq.com/docs/rate-limits).
    # These are organization-wide, not per-session - check your own account's
    # Limits page and adjust if you're on a different plan.
    rpm_limit_cheap: int = 30
    tpm_limit_cheap: int = 8_000
    rpm_limit_expensive: int = 30
    tpm_limit_expensive: int = 8_000

    max_concurrent_requests: int = 5
    concurrency_queue_timeout_seconds: float = 30.0

    per_user_rpm_limit: int = 10

    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_cooldown_seconds: int = 30

    backoff_base_seconds: float = 1.0
    backoff_max_retries: int = 3

    daily_token_budget_global: int = 200_000
    daily_token_budget_per_session: int = 20_000

    redis_url: str = "redis://localhost:6379"
    redis_index_name: str = "legal_chunks"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    reranker_model: str = "BAAI/bge-reranker-base"

    top_k_retrieve: int = 10
    top_k_rerank: int = 4
    # bge-reranker-base cross-encoder scores (post-sigmoid, 0-1) for this
    # corpus: genuinely relevant chunks score ~0.9+, unrelated ones ~0.0001-
    # 0.002 - there's no gradual middle, so a low threshold cleanly separates
    # them. Below this, a chunk is dropped rather than stuffed into context
    # (KNN vector search always returns *something* even when nothing in the
    # index is actually relevant to the question).
    min_rerank_score: float = 0.1

    chunk_size_tokens: int = 600
    chunk_overlap_tokens: int = 90

    seed_corpus_dir: str = "data/sample_case_law"

    redis_cache_index_name: str = "legal_qa_cache"
    semantic_cache_similarity_threshold: float = 0.95
    semantic_cache_ttl_seconds: int = 86_400

    conversation_memory_turns: int = 6
    conversation_memory_ttl_seconds: int = 7_200
    # Separate from conversation_memory_turns: that cap keeps LLM prompt
    # context small, this one is just how much chat the UI can rehydrate
    # after a reload, so it can afford to be larger.
    chat_history_max_turns: int = 50

    difficulty_word_threshold: int = 40

    # Multi-query retrieval: an extra cheap-model call decomposes "hard"
    # (multi-part/analytical) questions into several targeted sub-queries
    # before retrieval, fanning out search across each rather than a single
    # blended embedding. Gated on difficulty rather than always-on to avoid
    # spending an LLM call on every simple factual lookup.
    enable_query_expansion: bool = True

    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"
    # Simple API key for protecting sensitive endpoints (escalations, usage)
    # Create a key and place it in .env as ADMIN_API_KEY=yourkey
    admin_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
