DISCLAIMER_TEXT = (
    "\n\nThis is legal research assistance, not legal advice. Verify against "
    "primary sources and consult a licensed advocate for advice on your "
    "specific situation."
)

_DISCLAIMER_MARKERS = ("not legal advice", "legal research assistance")


def ensure_disclaimer(answer: str) -> tuple[str, bool]:
    lowered = answer.lower()
    if any(marker in lowered for marker in _DISCLAIMER_MARKERS):
        return answer, False
    return answer + DISCLAIMER_TEXT, True
