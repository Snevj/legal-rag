import re

_CASE_CITATION = re.compile(r"[A-Z][A-Za-z.]+ v\.? [A-Z][A-Za-z.]+")


def compute_grounding(answer: str, sources: list[dict]) -> tuple[float, list[str]]:
    """Lexical-overlap heuristic (not semantic/embedding-based): what
    fraction of the answer's significant words also appear in the retrieved
    source text, plus a check for case names the answer cites that don't
    match any actually-retrieved source title. Flags likely hallucination;
    doesn't prove correctness."""
    if not sources:
        return 0.0, []

    combined_source_text = " ".join(s["text"] for s in sources).lower()
    answer_words = set(re.findall(r"[a-zA-Z]{4,}", answer.lower()))
    if not answer_words:
        return 0.0, []

    overlap = sum(1 for word in answer_words if word in combined_source_text)
    grounding_score = round(overlap / len(answer_words), 3)

    source_titles = [s["source_title"] for s in sources]
    cited_cases = set(_CASE_CITATION.findall(answer))
    ungrounded = [
        case
        for case in cited_cases
        if not any(case.split(" v")[0].strip() in title for title in source_titles)
    ]

    return grounding_score, ungrounded
