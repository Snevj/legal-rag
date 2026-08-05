from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from langfuse import Langfuse

from app.config import get_settings


def is_enabled() -> bool:
    settings = get_settings()
    return bool(settings.langfuse_public_key and settings.langfuse_secret_key)


@lru_cache
def _client() -> Langfuse | None:
    if not is_enabled():
        return None
    settings = get_settings()
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


class _NoOpSpan:
    def update(self, **kwargs: Any) -> None:
        pass


@contextmanager
def trace_query(question: str, session_id: str):
    """Wraps a /query request in a Langfuse trace span. No-ops cleanly if
    Langfuse isn't configured - tracing is optional, like Groq's key it
    requires the user's own free account, so the app must run fine without it."""
    client = _client()
    if client is None:
        yield _NoOpSpan()
        return

    with client.start_as_current_observation(
        name="query",
        as_type="span",
        input={"question": question},
        metadata={"session_id": session_id},
    ) as span:
        yield span


def record_generation(
    model: str,
    question: str,
    context_length: int,
    answer: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
    latency_ms: float,
) -> None:
    client = _client()
    if client is None:
        return
    obs = client.start_observation(
        name="groq-generate",
        as_type="generation",
        input={"question": question, "context_length": context_length},
        output=answer,
        model=model,
        usage_details={"input": prompt_tokens, "output": completion_tokens},
        cost_details={"total": cost_usd},
        metadata={"latency_ms": latency_ms},
    )
    obs.end()


def flush() -> None:
    client = _client()
    if client is not None:
        client.flush()
