from app.cache.semantic_cache import get_semantic_cache
from app.config import get_settings
from app.embeddings.embedder import get_embedder
from app.embeddings.reranker import get_reranker
from app.graph.state import RagState
from app.guardrails.disclaimer import ensure_disclaimer
from app.guardrails.grounding import compute_grounding
from app.guardrails.pii import detect_pii
from app.guardrails.prompt_injection import detect_injection
from app.hitl.escalation import get_escalation_queue
from app.llm import gateway as llm_gateway
from app.memory.conversation import get_conversation_memory
from app.vectorstore.redis_store import get_vector_store

_LOW_GROUNDING_THRESHOLD = 0.15  # grounding_score is a rough lexical-overlap ratio, not a calibrated probability

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

    query_vector = state.get("question_embedding") or get_embedder().embed_query(state["question"])
    hits = store.search(query_vector, top_k=settings.top_k_retrieve)

    retrieved = [
        {
            "doc_id": h["doc_id"],
            "source_title": h["source_title"],
            "chunk_index": h["chunk_index"],
            "text": h["text"],
            "score": h["distance"],
        }
        for h in hits
    ]
    return {"retrieved": retrieved}


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
    "primary sources and consult a licensed attorney for advice on your "
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

    result = llm_gateway.generate(
        question=state["question"],
        context=context,
        session_id=state["session_id"],
        preferred_model=state.get("model_choice", settings.groq_model_expensive),
        history=state.get("history", ""),
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
