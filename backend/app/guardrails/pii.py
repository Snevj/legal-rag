import re

# Heuristic, not exhaustive - regexes will miss many real-world PII formats
# (international phone numbers, non-US SSN-equivalents, etc). Good enough as
# a flagging signal for escalation/tracing; not a compliance guarantee.
_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
}


def detect_pii(text: str) -> list[str]:
    return [label for label, pattern in _PATTERNS.items() if pattern.search(text)]


def redact_pii(text: str) -> tuple[str, list[str]]:
    found: list[str] = []
    redacted = text
    for label, pattern in _PATTERNS.items():
        if pattern.search(redacted):
            found.append(label)
            redacted = pattern.sub(f"[REDACTED_{label.upper()}]", redacted)
    return redacted, found
