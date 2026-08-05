# Heuristic phrase list, not a robust classifier - defense-in-depth alongside
# the <untrusted_context> delimiting done in the system prompt itself
# (see app/llm/groq_client.py). Catches unsophisticated attempts; a
# determined attacker can phrase around a fixed phrase list.
_INJECTION_PHRASES = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignore the above",
    "disregard the above",
    "disregard previous instructions",
    "you are now",
    "reveal your system prompt",
    "reveal your instructions",
    "print your instructions",
    "new instructions:",
    "act as",
    "pretend you are",
    "jailbreak",
    "do anything now",
)


def detect_injection(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in _INJECTION_PHRASES)
