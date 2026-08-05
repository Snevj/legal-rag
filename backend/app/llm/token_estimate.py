from app.ingestion.chunking import CHARS_PER_TOKEN
from app.llm.groq_client import SYSTEM_PROMPT


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_prompt_tokens(context: str, question: str) -> int:
    """Pre-flight estimate of the full request, before it's queued for rate-limit
    capacity. Deliberately conservative (chars/4, no real tokenizer) - good enough
    to size-check against bucket capacity and budgets without adding a tokenizer
    dependency for a model we don't control the exact tokenizer of anyway."""
    return estimate_tokens(SYSTEM_PROMPT) + estimate_tokens(context) + estimate_tokens(question)
