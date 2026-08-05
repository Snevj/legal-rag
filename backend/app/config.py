from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str
    groq_model_cheap: str = "llama-3.1-8b-instant"
    groq_model_expensive: str = "llama-3.3-70b-versatile"

    # Free-tier limits per Groq's published docs (console.groq.com/docs/rate-limits).
    # These are organization-wide, not per-session - check your own account's
    # Limits page and adjust if you're on a different plan.
    rpm_limit_cheap: int = 30
    tpm_limit_cheap: int = 6_000
    rpm_limit_expensive: int = 30
    tpm_limit_expensive: int = 12_000

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

    chunk_size_tokens: int = 600
    chunk_overlap_tokens: int = 90

    seed_corpus_dir: str = "data/sample_case_law"

    redis_cache_index_name: str = "legal_qa_cache"
    semantic_cache_similarity_threshold: float = 0.95
    semantic_cache_ttl_seconds: int = 86_400

    conversation_memory_turns: int = 6
    conversation_memory_ttl_seconds: int = 7_200

    difficulty_word_threshold: int = 40

    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
