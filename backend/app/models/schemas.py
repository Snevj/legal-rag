from pydantic import BaseModel, Field


class SourceChunk(BaseModel):
    doc_id: str
    source_title: str
    chunk_index: int
    text: str
    score: float


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str | None = None
    priority: int = Field(default=5, ge=0, le=9)
    request_human_review: bool = False


class GuardrailInfo(BaseModel):
    input_pii_detected: bool
    input_pii_types: list[str]
    injection_flagged: bool
    output_pii_detected: bool
    output_pii_types: list[str]
    grounding_score: float
    ungrounded_citations: list[str]
    disclaimer_added: bool


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    session_id: str
    model_used: str
    difficulty: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: float
    cache_hit: bool
    guardrails: GuardrailInfo
    escalated: bool
    escalation_reasons: list[str]


class IngestResponse(BaseModel):
    doc_id: str
    source_title: str
    num_chunks: int


class HealthResponse(BaseModel):
    status: str
    redis_connected: bool


class UsageResponse(BaseModel):
    date: str
    global_tokens_used: int
    global_cost_usd: float
    global_token_budget: int
    session_tokens_used: int | None = None
    session_cost_usd: float | None = None
    session_token_budget: int | None = None
