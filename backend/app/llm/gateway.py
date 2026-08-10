import time
from dataclasses import dataclass

from groq import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from app.config import get_settings
from app.cost.budget import get_budget_tracker
from app.llm.circuit_breaker import get_circuit_breakers
from app.llm.concurrency import QueueTimeoutError, get_concurrency_limiter
from app.llm.groq_client import get_groq_client
from app.llm.pricing import estimate_cost_usd
from app.llm.token_bucket import get_model_buckets
from app.llm.token_estimate import estimate_prompt_tokens
from app.llm.user_throttle import get_user_throttle
from app.tracing.langfuse_client import record_generation

RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)


class GatewayError(Exception):
    pass


class UserThrottledError(GatewayError):
    pass


class AllModelsUnavailableError(GatewayError):
    pass


@dataclass
class GatewayResult:
    answer: str
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: float


def _other_model(model: str) -> str:
    settings = get_settings()
    return settings.groq_model_expensive if model == settings.groq_model_cheap else settings.groq_model_cheap


def expand_query(question: str, session_id: str) -> list[str]:
    """Best-effort query decomposition for multi-query retrieval: always
    uses the cheap model, and fails open (returns []) on any error - budget
    exhaustion, rate limit, malformed response - rather than raising, since
    this is a retrieval-quality enhancement, not a step the pipeline should
    ever block on. retrieve_node falls back to single-query search on []."""
    settings = get_settings()
    try:
        budget = get_budget_tracker()
        breakers = get_circuit_breakers()
        buckets = get_model_buckets()
        model = settings.groq_model_cheap

        if breakers[model].is_open():
            return []

        estimated_tokens = estimate_prompt_tokens("", question)
        budget.check_preflight(session_id, estimated_tokens)
        if not buckets[model].try_consume(estimated_tokens):
            return []

        client = get_groq_client()
        retryer = Retrying(
            retry=retry_if_exception_type(RETRYABLE_ERRORS),
            wait=wait_random_exponential(multiplier=settings.backoff_base_seconds, max=10),
            stop=stop_after_attempt(2),
            reraise=True,
        )
        queries, prompt_tokens, completion_tokens = retryer(client.expand_query, model, question)

        breakers[model].record_success()
        cost_usd = estimate_cost_usd(model, prompt_tokens, completion_tokens)
        budget.record_usage(session_id, prompt_tokens + completion_tokens, cost_usd)
        return queries
    except Exception:  # noqa: BLE001 - any failure here degrades to single-query retrieval, never blocks the pipeline
        return []


def _call_with_retry(model: str, question: str, context: str, history: str):
    settings = get_settings()
    client = get_groq_client()
    retryer = Retrying(
        retry=retry_if_exception_type(RETRYABLE_ERRORS),
        wait=wait_random_exponential(multiplier=settings.backoff_base_seconds, max=20),
        stop=stop_after_attempt(settings.backoff_max_retries + 1),
        reraise=True,
    )
    return retryer(client.generate, model, question, context, history)


def generate(
    question: str,
    context: str,
    session_id: str,
    preferred_model: str,
    history: str = "",
    priority: int = 5,
) -> GatewayResult:
    """Resilient wrapper around the Groq call: concurrency cap, per-user
    throttle, pre-flight budget check, dual token-bucket rate limiting,
    backoff+jitter retries, circuit breaker, and cheap<->expensive fallback."""
    settings = get_settings()
    limiter = get_concurrency_limiter()
    throttle = get_user_throttle()
    buckets = get_model_buckets()
    breakers = get_circuit_breakers()
    budget = get_budget_tracker()

    if not throttle.check_and_increment(session_id):
        raise UserThrottledError("This session is sending requests too quickly. Please slow down.")

    estimated_tokens = estimate_prompt_tokens(context, question)
    # Pre-flight budget check happens before queuing so an over-budget request
    # never occupies a concurrency slot it was never going to be allowed to use.
    budget.check_preflight(session_id, estimated_tokens)

    start = time.perf_counter()
    try:
        limiter.acquire(priority=priority, timeout=settings.concurrency_queue_timeout_seconds)
    except QueueTimeoutError as exc:
        raise GatewayError("Server is at capacity; please retry shortly.") from exc

    try:
        candidates = [preferred_model, _other_model(preferred_model)]
        last_error: Exception | None = None

        for model in candidates:
            breaker = breakers[model]
            bucket = buckets[model]

            if breaker.is_open():
                continue
            if estimated_tokens > bucket.tpm_capacity:
                # This single request can never fit this model's bucket, no
                # matter how long we wait - skip straight to the other model.
                continue
            if not bucket.try_consume(estimated_tokens):
                continue  # no capacity left this minute - try the fallback model

            try:
                result = _call_with_retry(model, question, context, history)
            except RETRYABLE_ERRORS as exc:
                breaker.record_failure()
                last_error = exc
                continue

            breaker.record_success()
            cost_usd = estimate_cost_usd(model, result.prompt_tokens, result.completion_tokens)
            actual_tokens = result.prompt_tokens + result.completion_tokens
            budget.record_usage(session_id, actual_tokens, cost_usd)
            latency_ms = (time.perf_counter() - start) * 1000

            record_generation(
                model=model,
                question=question,
                context_length=len(context),
                answer=result.answer,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
            )

            return GatewayResult(
                answer=result.answer,
                model_used=model,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
            )

        raise AllModelsUnavailableError(
            "Both models are rate-limited, circuit-broken, or failing right now."
        ) from last_error
    finally:
        limiter.release()
