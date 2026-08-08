export interface SourceChunk {
  doc_id: string;
  source_title: string;
  chunk_index: number;
  text: string;
  score: number;
}

export interface GuardrailInfo {
  input_pii_detected: boolean;
  input_pii_types: string[];
  injection_flagged: boolean;
  output_pii_detected: boolean;
  output_pii_types: string[];
  grounding_score: number;
  ungrounded_citations: string[];
  disclaimer_added: boolean;
}

export interface QueryResponse {
  answer: string;
  sources: SourceChunk[];
  session_id: string;
  model_used: string;
  difficulty: string;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  latency_ms: number;
  cache_hit: boolean;
  guardrails: GuardrailInfo;
  escalated: boolean;
  escalation_reasons: string[];
}

export interface IngestResponse {
  doc_id: string;
  source_title: string;
  num_chunks: number;
}

export interface HealthResponse {
  status: string;
  redis_connected: boolean;
}

export interface UsageResponse {
  date: string;
  global_tokens_used: number;
  global_cost_usd: number;
  global_token_budget: number;
  session_tokens_used: number | null;
  session_cost_usd: number | null;
  session_token_budget: number | null;
}

export interface EscalationRecord {
  id: string;
  session_id: string;
  question: string;
  answer: string;
  reasons: string[];
  created_at: number;
  status: "pending" | "resolved";
  resolution_notes?: string;
  resolved_at?: number;
}

export interface ApiErrorBody {
  detail?: string;
}

/** One turn in the chat transcript, pairing the request with its full
 * response so the technical panel can show the exact backend payload. */
export interface ChatTurn {
  id: string;
  question: string;
  response: QueryResponse | null;
  error: string | null;
  pending: boolean;
  askedAt: number;
}
