"""Hard citation gate: unlike grounding.py's ungrounded_citations (which
only checks the answer's cited case names against sources retrieved *for
this query*), this checks against every document title ever ingested into
the corpus. A citation absent from *retrieval* might just mean the reranker
missed it; a citation absent from the *entire corpus* has no possible
grounding and is a fabrication - that distinction is what makes this a hard
veto rather than a soft escalation signal, following the same reasoning as
Falkor-IRAC's Verifier Agent (arXiv:2605.14665): a plausible but
unverifiable citation is worse than no citation, so it's rejected outright
rather than surfaced with reduced confidence.
"""

import re

from app.vectorstore.redis_store import get_vector_store

_CASE_CITATION = re.compile(r"[A-Z][A-Za-z.]+ v\.? [A-Z][A-Za-z.]+")


def _case_matches_title(case_name: str, title: str) -> bool:
    return case_name.split(" v")[0].strip() in title


def find_fabricated_citations(answer: str) -> list[str]:
    """Returns cited case names with zero match anywhere in the ingested
    corpus - not just outside this query's retrieved chunks."""
    cited_cases = set(_CASE_CITATION.findall(answer))
    if not cited_cases:
        return []

    known_titles = get_vector_store().known_titles()
    return [case for case in cited_cases if not any(_case_matches_title(case, title) for title in known_titles)]
