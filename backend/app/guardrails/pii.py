import re

# Heuristic, not exhaustive - regexes will miss many real-world PII formats.
# Good enough as a flagging signal for escalation/tracing; not a compliance
# guarantee. Aadhaar/PAN are the two identifiers most likely to show up in
# an Indian client's question (analogous to SSN/driver's license in a US
# context) - kept SSN/US phone too since either could still appear in a
# cross-border matter.
_PATTERNS = {
    "aadhaar": re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b"),
    "pan": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "phone_in": re.compile(r"\b(?:\+?91[-.\s]?)?[6-9]\d{9}\b"),
    "phone_us": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
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
