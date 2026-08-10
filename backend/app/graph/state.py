from typing import TypedDict


class SourceRef(TypedDict):
    doc_id: str
    source_title: str
    chunk_index: int
    text: str
    score: float


class RagState(TypedDict, total=False):
    question: str
    session_id: str
    priority: int
    request_human_review: bool

    difficulty: str
    model_choice: str

    input_pii_types: list[str]
    injection_flagged: bool

    history: str
    question_embedding: list[float]
    cache_hit: bool

    expanded_queries: list[str]
    session_upload_doc_id: str | None
    retrieved: list[SourceRef]
    reranked: list[SourceRef]

    answer: str
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: float

    citation_check_attempts: int
    citation_check_retry: bool
    citation_revision_note: str
    fabricated_citations: list[str]

    output_pii_types: list[str]
    grounding_score: float
    ungrounded_citations: list[str]
    disclaimer_added: bool

    escalated: bool
    escalation_reasons: list[str]
