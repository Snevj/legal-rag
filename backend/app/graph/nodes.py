from app.cache.semantic_cache import get_semantic_cache
from app.config import get_settings
from app.embeddings.embedder import get_embedder
from app.embeddings.reranker import get_reranker
from app.graph.state import RagState
from app.guardrails.citation_registry import find_fabricated_citations
from app.guardrails.disclaimer import ensure_disclaimer
from app.guardrails.grounding import compute_grounding
from app.guardrails.pii import detect_pii
from app.guardrails.prompt_injection import detect_injection
from app.hitl.escalation import get_escalation_queue
from app.llm import gateway as llm_gateway
from app.memory.conversation import get_conversation_memory
from app.vectorstore.redis_store import get_vector_store

_LOW_GROUNDING_THRESHOLD = 0.15  # grounding_score is a rough lexical-overlap ratio, not a calibrated probability
_MAX_CITATION_REVISION_ATTEMPTS = 2

_HARD_QUESTION_KEYWORDS = (
    "compare",
    "distinguish",
    "analyze",
    "analyse",
    "implications",
    "explain why",
    "difference between",
    "how does",
    "relationship between",
    "reconcile",
)


def route_node(state: RagState) -> dict:
    """Cheap heuristic difficulty classifier - no extra LLM call, just word
    count and a few analytical-phrasing signals. Picks the model tier so
    simple lookups don't spend expensive-model budget."""
    settings = get_settings()
    question = state["question"]
    lowered = question.lower()

    is_hard = (
        len(question.split()) > settings.difficulty_word_threshold
        or question.count("?") > 1
        or any(keyword in lowered for keyword in _HARD_QUESTION_KEYWORDS)
    )

    difficulty = "hard" if is_hard else "easy"
    model_choice = settings.groq_model_expensive if is_hard else settings.groq_model_cheap
    return {"difficulty": difficulty, "model_choice": model_choice}


def input_guardrail_node(state: RagState) -> dict:
    """Scans the raw question. We don't mutate or block on this - it's the
    user's own (privileged) input - but flag it for the response/escalation
    and to keep it out of external traces unredacted (see app/tracing)."""
    question = state["question"]
    return {
        "input_pii_types": detect_pii(question),
        "injection_flagged": detect_injection(question),
    }


def memory_load_node(state: RagState) -> dict:
    memory = get_conversation_memory()
    return {"history": memory.load(state["session_id"])}


def cache_lookup_node(state: RagState) -> dict:
    embedder = get_embedder()
    cache = get_semantic_cache()

    query_vector = embedder.embed_query(state["question"])
    cached = cache.lookup(query_vector)

    if cached is None:
        return {"cache_hit": False, "question_embedding": query_vector}

    return {
        "cache_hit": True,
        "answer": cached["answer"],
        "reranked": cached["reranked"],
        "model_used": cached["model_used"],
        "difficulty": cached["difficulty"],
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cost_usd": 0.0,
        "latency_ms": 0.0,
        "output_pii_types": cached["output_pii_types"],
        "grounding_score": cached["grounding_score"],
        "ungrounded_citations": cached["ungrounded_citations"],
        "disclaimer_added": cached["disclaimer_added"],
    }


def retrieve_node(state: RagState) -> dict:
    settings = get_settings()
    store = get_vector_store()
    embedder = get_embedder()
    question = state["question"]

    # Query expansion only for "hard" (multi-part/analytical) questions -
    # route_node already classified difficulty, and a single embedding of a
    # blended multi-issue question tends to retrieve a compromise match for
    # each part rather than a strong match for any one of them. Simple
    # factual lookups don't need the extra LLM call.
    expanded_queries: list[str] = []
    if settings.enable_query_expansion and state.get("difficulty") == "hard":
        expanded_queries = llm_gateway.expand_query(question, state["session_id"])

    sub_queries = [question] + [q for q in expanded_queries if q.strip().lower() != question.strip().lower()]
    per_query_top_k = settings.top_k_retrieve if len(sub_queries) == 1 else max(
        settings.top_k_retrieve // len(sub_queries), settings.top_k_rerank
    )

    # Merge across sub-queries by (doc_id, chunk_index), keeping each
    # chunk's best (lowest) distance score across all the queries that
    # retrieved it.
    merged: dict[tuple[str, int], dict] = {}
    for i, q in enumerate(sub_queries):
        query_vector = (
            state.get("question_embedding")
            if i == 0 and state.get("question_embedding")
            else embedder.embed_query(q)
        )
        for h in store.search(query_vector, top_k=per_query_top_k):
            key = (h["doc_id"], h["chunk_index"])
            if key not in merged or h["distance"] < merged[key]["distance"]:
                merged[key] = h

    retrieved = [
        {
            "doc_id": h["doc_id"],
            "source_title": h["source_title"],
            "chunk_index": h["chunk_index"],
            "text": h["text"],
            "score": h["distance"],
        }
        for h in merged.values()
    ]
    return {"retrieved": retrieved, "expanded_queries": expanded_queries}


def rerank_node(state: RagState) -> dict:
    settings = get_settings()
    reranker = get_reranker()

    candidates = [(item["text"], item) for item in state["retrieved"]]
    top = reranker.rerank(state["question"], candidates, top_k=settings.top_k_rerank)

    # KNN vector search always returns its top_k nearest neighbors even when
    # nothing in the index is actually relevant to the question - dropping
    # sub-threshold chunks here (rather than after generation) keeps them out
    # of both the LLM context and the API response's `sources`, so the model
    # can't cite an irrelevant case just because it happened to be nearby in
    # embedding space.
    reranked = [
        {**metadata, "score": score}
        for _, metadata, score in top
        if score >= settings.min_rerank_score
    ]
    return {"reranked": reranked}


_NO_CONTEXT_ANSWER = (
    "No indexed document appears relevant to this question. Try rephrasing, "
    "or upload a document that covers this topic.\n\n"
    "This is legal research assistance, not legal advice. Verify against "
    "primary sources and consult a licensed advocate for advice on your "
    "specific situation."
)


def generate_node(state: RagState) -> dict:
    settings = get_settings()

    if not state["reranked"]:
        return {
            "answer": _NO_CONTEXT_ANSWER,
            "model_used": "none",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost_usd": 0.0,
            "latency_ms": 0.0,
        }

    context = "\n\n---\n\n".join(
        f"[{item['source_title']}, chunk {item['chunk_index']}]\n{item['text']}"
        for item in state["reranked"]
    )

    history = state.get("history", "")
    revision_note = state.get("citation_revision_note")
    if revision_note:
        # citation_gate_node kicked the answer back for citing a case that
        # doesn't exist anywhere in the corpus - fed in as history so the
        # model sees it as prior conversation context to correct, not as
        # part of the (untrusted) retrieved document context.
        history = f"{history}\n\n[System correction: {revision_note}]".strip()

    result = llm_gateway.generate(
        question=state["question"],
        context=context,
        session_id=state["session_id"],
        preferred_model=state.get("model_choice", settings.groq_model_expensive),
        history=history,
        priority=state.get("priority", 5),
    )

    return {
        "answer": result.answer,
        "model_used": result.model_used,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "cost_usd": result.cost_usd,
        "latency_ms": result.latency_ms,
    }


_CITATION_ABSTAIN_ANSWER = (
    "I could not produce an answer whose citations are verifiable against "
    "the indexed corpus after {attempts} revision attempt(s) - the case(s) "
    "cited ({cases}) do not exist anywhere in the ingested documents. "
    "Rather than return an answer citing a case that may not exist, no "
    "verified answer is available for this question.\n\n"
    "This is legal research assistance, not legal advice. Verify against "
    "primary sources and consult a licensed advocate for advice on your "
    "specific situation."
)


def citation_gate_node(state: RagState) -> dict:
    """Hard veto, not a soft score: a case citation with zero match anywhere
    in the ingested corpus (checked via app.guardrails.citation_registry,
    corpus-wide - not just this query's retrieved chunks, which is what
    output_guardrail_node's ungrounded_citations checks) gets one revision
    attempt or two before the answer is replaced with an explicit
    abstention rather than shipped to the user as-is."""
    fabricated = find_fabricated_citations(state["answer"])
    if not fabricated:
        return {"citation_check_retry": False, "fabricated_citations": []}

    attempts = state.get("citation_check_attempts", 0)
    if attempts < _MAX_CITATION_REVISION_ATTEMPTS:
        return {
            "citation_check_retry": True,
            "citation_check_attempts": attempts + 1,
            "citation_revision_note": (
                f"Your previous answer cited {', '.join(fabricated)}, which "
                "does not exist anywhere in the indexed corpus. Do not cite "
                "it. Answer again using only cases that are actually in the "
                "provided context, or state plainly that no relevant "
                "precedent was found."
            ),
            "fabricated_citations": fabricated,
        }

    return {
        "citation_check_retry": False,
        "answer": _CITATION_ABSTAIN_ANSWER.format(attempts=attempts, cases=", ".join(fabricated)),
        "fabricated_citations": fabricated,
    }


def output_guardrail_node(state: RagState) -> dict:
    grounding_score, ungrounded_citations = compute_grounding(state["answer"], state["reranked"])
    answer, disclaimer_added = ensure_disclaimer(state["answer"])

    return {
        "answer": answer,
        "output_pii_types": detect_pii(state["answer"]),
        "grounding_score": grounding_score,
        "ungrounded_citations": ungrounded_citations,
        "disclaimer_added": disclaimer_added,
    }


def escalation_node(state: RagState) -> dict:
    reasons = []
    if state.get("request_human_review"):
        reasons.append("user_requested_review")
    if state.get("injection_flagged"):
        reasons.append("prompt_injection_detected")
    if state.get("input_pii_types"):
        reasons.append("input_pii_detected")
    if state.get("output_pii_types"):
        reasons.append("output_pii_detected")
    if state.get("ungrounded_citations"):
        reasons.append("ungrounded_citation")
    if state.get("grounding_score", 1.0) < _LOW_GROUNDING_THRESHOLD:
        reasons.append("low_grounding_score")
    if state.get("fabricated_citations"):
        reasons.append("fabricated_citation_hard_gate")

    escalated = bool(reasons)
    if escalated:
        get_escalation_queue().add(
            session_id=state["session_id"],
            question=state["question"],
            answer=state["answer"],
            reasons=reasons,
        )

    return {"escalated": escalated, "escalation_reasons": reasons}


def memory_store_node(state: RagState) -> dict:
    memory = get_conversation_memory()
    memory.append(state["session_id"], state["question"], state["answer"])
    return {}


def cache_store_node(state: RagState) -> dict:
    cache = get_semantic_cache()
    query_vector = state.get("question_embedding") or get_embedder().embed_query(state["question"])
    payload = {
        "answer": state["answer"],
        "reranked": state["reranked"],
        "model_used": state["model_used"],
        "difficulty": state["difficulty"],
        "output_pii_types": state.get("output_pii_types", []),
        "grounding_score": state.get("grounding_score", 0.0),
        "ungrounded_citations": state.get("ungrounded_citations", []),
        "disclaimer_added": state.get("disclaimer_added", False),
    }
    cache.store(query_vector, state["question"], payload)
    return {}
