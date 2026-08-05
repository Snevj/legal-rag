# Published per-token pricing from console.groq.com/docs/models (checked at
# implementation time). This is for cost *tracking/estimation* on your own
# usage - Groq's free tier isn't metered billing, but knowing the equivalent
# cost is exactly the "cost tracing" this module exists for. Re-check the
# docs page and update if Groq changes pricing.
PRICING_PER_MILLION_TOKENS = {
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
}


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = PRICING_PER_MILLION_TOKENS.get(model)
    if rates is None:
        return 0.0
    return (prompt_tokens * rates["input"] + completion_tokens * rates["output"]) / 1_000_000
