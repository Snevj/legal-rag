# Legal RAG Assistant — Phase 1: Core Pipeline

## Context

Building a RAG application for lawyers to ask questions about case law/legal documents, with a long list of production features (guardrails, evals, multimodal, tracing, cost routing, HITL, caching, red-teaming, agent memory) plus a sleek frontend and free-tier Docker/AWS deployment. This is greenfield — the working directory (`/Users/snehvijayvergiya/claude`) is empty, no existing code to build on.

Given the scope, the user chose a **phased build**: get a real, working retrieve→rerank→generate pipeline behind a FastAPI backend first, verify it end-to-end, then layer in the advanced features. This plan covers **Phase 1 only**. Later phases (not being built yet, listed for visibility):
- **Phase 2**: guardrails (citation/grounding verification, PII redaction, UPL disclaimers), Ragas evals, Langfuse tracing, Redis semantic caching, Groq model routing (8B vs 70B by difficulty), human-in-the-loop escalation, agent memory, red-teaming notes.
- **Phase 3**: Next.js + Tailwind + shadcn/ui frontend.
- **Phase 4**: Docker Compose hardening + AWS free-tier deployment (EC2 + S3).

Confirmed decisions from the user: Groq-only (no second LLM provider), local embeddings/reranking (no paid embedding API), Redis Stack as the vector DB, seed the dev environment with public-domain case law text so ingestion/retrieval can be tested with realistic legal documents immediately.

## Scope of Phase 1

A working, testable pipeline — no guardrails, evals, tracing, caching, routing, or frontend yet. Those are explicitly deferred to Phase 2/3 so this phase ships something real and verifiable rather than a pile of stubs.

**What Phase 1 delivers:**
- FastAPI backend with `/ingest`, `/query`, `/health` endpoints
- Document ingestion: PDF/TXT upload → text extraction → legal-aware chunking → local embedding → upsert into Redis vector index
- LangGraph pipeline: `retrieve → rerank → generate` as a compiled graph (this graph is the extension point Phase 2 builds on — adding guardrail/eval/routing nodes without restructuring)
- Redis Stack (via Docker) as the vector store, using RediSearch vector similarity
- Local embedding model (`BAAI/bge-small-en-v1.5` via `sentence-transformers`) — no API cost, no rate limit
- Local cross-encoder reranker (`BAAI/bge-reranker-base`)
- Groq `llama-3.3-70b-versatile` for generation (single model in Phase 1 — cheap/expensive routing arrives Phase 2)
- Seed corpus: ~8-10 public-domain U.S. Supreme Court opinions (full text, no copyright/API-key issues) bundled as `.txt` files and ingested through the real ingestion pipeline, so retrieval can be tested against genuine legal text
- Docker Compose wiring redis-stack + backend together
- One end-to-end pytest that ingests the seed corpus and asks a real question, asserting an answer with cited sources comes back

**Explicitly NOT in Phase 1:** guardrails, Ragas, Langfuse, caching, cost routing, HITL, frontend, AWS deployment. These come in later phases per the user's phasing choice.

## Project Structure

```
legal-rag/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app + router registration
│   │   ├── config.py                  # pydantic Settings: GROQ_API_KEY, REDIS_URL, model names
│   │   ├── api/routes/
│   │   │   ├── ingest.py              # POST /ingest — multipart file upload
│   │   │   ├── query.py               # POST /query — {question} -> {answer, sources}
│   │   │   └── health.py              # GET /health
│   │   ├── ingestion/
│   │   │   ├── loaders.py             # PDF/TXT extraction (pypdf + plain text)
│   │   │   ├── chunking.py            # recursive splitter w/ legal-aware separators (sections, paragraphs), attaches doc_id/chunk_id/page metadata
│   │   │   └── seed_corpus.py         # loads data/sample_case_law/*.txt through the same ingestion path
│   │   ├── embeddings/
│   │   │   ├── embedder.py            # sentence-transformers wrapper (bge-small)
│   │   │   └── reranker.py            # cross-encoder wrapper (bge-reranker-base)
│   │   ├── vectorstore/
│   │   │   └── redis_store.py         # index creation, upsert, KNN search via redis-py
│   │   ├── graph/
│   │   │   ├── state.py               # LangGraph TypedDict state (question, retrieved_chunks, reranked_chunks, answer, sources)
│   │   │   ├── nodes.py               # retrieve_node, rerank_node, generate_node
│   │   │   └── pipeline.py            # StateGraph construction + compile()
│   │   ├── llm/
│   │   │   └── groq_client.py         # thin Groq SDK wrapper
│   │   └── models/schemas.py          # pydantic request/response models
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/test_query_e2e.py
├── data/sample_case_law/              # seeded public-domain opinion text files
├── docker-compose.yml                 # redis-stack + backend services
├── .env.example                       # GROQ_API_KEY=, REDIS_URL=
└── README.md                          # setup + how to run
```

## Key Implementation Notes

- **Chunking**: legal documents have strong internal structure (numbered sections, paragraphs, headnotes). Use a recursive splitter with a separator priority list (`\n\n\n`, section headers, `\n\n`, `\n`, sentence) rather than fixed-size chunking, target ~500-800 tokens/chunk with ~15% overlap, and always carry `doc_id`, `source_title`, `chunk_index` as Redis hash fields alongside the vector so `/query` can cite sources precisely.
- **Redis vector index**: use `redis-py`'s `redis.commands.search` (RediSearch module, included in the `redis/redis-stack` image) with a `HNSW` or `FLAT` vector field, `COSINE` distance, dim=384 (bge-small's output size).
- **LangGraph graph** is intentionally the seam for Phase 2: `retrieve_node` and `generate_node` will later get a `guardrail_node` and `route_node` inserted around them, so the state schema is designed to carry a superset of fields now (e.g. `difficulty: Optional[str] = None`) even though only Phase 1 fields are populated today.
- **Seed corpus acquisition**: fetch full-text of well-known, unambiguously public-domain SCOTUS opinions (e.g. Marbury v. Madison, Brown v. Board of Education, Miranda v. Arizona) as static text — no live scraping API dependency for Phase 1, so ingestion is testable offline and deterministically.
- **Groq key**: the user needs to create a free Groq API key themselves at console.groq.com and supply it via `.env` — account creation isn't something I can do on their behalf.

## Verification

1. `docker compose up -d` — brings up Redis Stack + backend.
2. Run seed ingestion (a one-off script or `POST /ingest` calls) to load the sample case law into Redis; confirm via RedisInsight or a debug endpoint that vectors were written.
3. `pytest backend/tests/test_query_e2e.py` — ingests seed corpus, asks a real question (e.g. "What did the Court hold about the right to counsel in Miranda v. Arizona?"), asserts the response contains a non-empty answer and at least one source citation matching the seeded corpus.
4. Manual sanity check via `curl localhost:8000/query` with a legal question, visually inspect the answer + cited chunks for plausibility.
5. Confirm `/health` returns 200 and Redis connectivity is healthy.

# UPDATED PLAN: Legal RAG Assistant — Phase 2: Guardrails, Cost/Rate Governance, Evals, Tracing, Memory

## Context

Phase 1 shipped a working `retrieve → rerank → generate` pipeline (FastAPI + LangGraph + Redis + local embeddings/reranker + Groq), verified end-to-end with a real Groq key and a passing pytest suite. The user now wants Phase 2: the production-hardening layer. Two things were emphasized explicitly:

1. **Cost/token tracing with hard budgets** — track token usage and cost per prompt, and make sure nobody (any one session, and the app overall) can blow through a token budget.
2. **A full concurrency + rate-limiting + resilience stack**, itemized by the user: concurrency limit, dual token bucket (RPM+TPM), pre-flight token estimation, per-user Redis-backed throttling, exponential backoff+jitter on 429s, priority queue, circuit breaker, fallback model.

Plus the rest of the originally-scoped Phase 2 items: guardrails (grounding/citation verification, PII handling, UPL disclaimers, prompt-injection defense), Ragas evals, Langfuse tracing, Redis semantic caching, cheap/expensive model routing, human-in-the-loop escalation, agent memory, red-teaming notes.

Confirmed decision: model fallback stays **within Groq** (cheap ↔ expensive model fail over into each other) — no second provider, no extra account signup needed.

## Design

### Graph shape (LangGraph)

```
START → route(difficulty) → cache_lookup ─┬─(hit)→ END
                                            └─(miss)→ memory_load → input_guardrail → retrieve → rerank
                                            → generate (via LLM Gateway) → output_guardrail → escalation_check
                                            → memory_store → cache_store → END
```

`route_node` is a cheap heuristic (word count, multi-part/analytical phrasing) picking `groq_model_cheap` (llama-3.1-8b-instant) vs `groq_model_expensive` (llama-3.3-70b-versatile) — no extra LLM call, deterministic, free.

### LLM Gateway (`backend/app/llm/`) — the resilience stack

New `gateway.py` wraps every Groq call, composing:
- **`concurrency.py`** — in-process `PriorityConcurrencyLimiter` (heap-based priority queue + semaphore semantics; lower priority number served first, FIFO tiebreak). Caps concurrent Groq calls (default 5); excess requests queue with a max-wait timeout → 503 if exceeded.
- **`token_estimate.py`** — chars/4 heuristic (same approach already used in `chunking.py`) to pre-flight-estimate prompt tokens *before* queuing for rate-limit capacity, so an over-sized request fails fast instead of occupying a slot it can never fill.
- **`token_bucket.py`** — Redis Lua-script-backed dual bucket (RPM + TPM) per model, atomic check-and-decrement, true refill-over-time semantics (not fixed-window).
- **`user_throttle.py`** — Redis fixed-window per-session request counter (anti-abuse, tighter than the global bucket).
- **`circuit_breaker.py`** — Redis-backed per-model breaker (closed/open/half-open); opens after N consecutive failures, cools down, then trials one request.
- Retry wrapper using `tenacity` for exponential backoff + jitter on Groq 429s/transient errors.
- **Fallback**: if the primary model's breaker is open or its bucket is exhausted after retries, the gateway calls the *other* Groq model instead and returns which model actually served the request.
- **`pricing.py`** — per-model $/1M-token table (fetched from Groq's current published pricing during implementation, not guessed) + cost calculator from `completion.usage`.

### Cost/budget enforcement (`backend/app/cost/budget.py`)

Redis-backed cumulative token/cost counters, both **global** (protects the one shared Groq key) and **per-session** (anti-abuse). Checked pre-flight using the token estimate (reject before spending anything if it would exceed budget), reconciled post-call with actual usage from the Groq response. `GET /usage` exposes current totals. Defaults configurable via env (e.g. daily global/session caps); documented as tune-to-taste.

### Guardrails (`backend/app/guardrails/`)

- `pii.py` — regex-based detect/redact (SSN, email, phone, credit card) on questions and answers.
- `prompt_injection.py` — heuristic scan for injection phrases in retrieved chunk text and user input (defense-in-depth on top of prompt-level delimiting of untrusted context).
- `grounding.py` — verifies cited source titles actually exist among the retrieved chunks; lexical-overlap-based grounding score; flags likely hallucinated citations.
- `disclaimer.py` — guarantees the "not legal advice" disclaimer is present in every answer, appending a canned one if the model omits it.

Wired in as `input_guardrail`/`output_guardrail` graph nodes; results (`grounding_score`, `pii_flagged`, `injection_flagged`) surface in the API response and feed escalation.

### Caching, memory, HITL

- `cache/semantic_cache.py` — separate Redis vector index; embed the question, KNN search for a near-duplicate prior question (cosine ≥ threshold), return the cached answer on hit (skips retrieve/rerank/generate entirely — real cost savings), TTL'd.
- `memory/conversation.py` — Redis-backed last-N-turns store keyed by `session_id`, loaded before generation and appended after, so follow-up questions work.
- `hitl/escalation.py` — Redis-backed escalation queue; a response is escalated on guardrail flags or explicit user request. `GET /escalations`, `POST /escalations/{id}/resolve`.
- `session_id` becomes the shared key across throttling, memory, and escalation — optional in `QueryRequest`, generated server-side and echoed back if omitted.

### Tracing (`backend/app/tracing/langfuse_client.py`)

Langfuse **Cloud free tier**, not self-hosted — self-hosting Langfuse now needs Postgres+ClickHouse+web+worker, which doesn't fit "free, low-resource, eventually on a t2/t3.micro." Optional config (like Groq, the user must create their own free account/keys — I can't do that for them); the client no-ops cleanly if unconfigured so the app still runs without it. One trace per `/query` call with spans per graph stage and a generation span capturing model, token usage, cost, latency, cache-hit status.

### Evals (`backend/app/evals/`)

Curated ~12-15 question/reference-answer pairs against the 5 seeded cases (`dataset.py`), run through the real pipeline, scored with Ragas (`faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`) using Groq as judge (`langchain-groq`) and the existing local embedder wrapped to satisfy Ragas' embeddings interface (no extra embedding dependency/cost). Runs as a script (`python -m app.evals.run_ragas`), like `seed_corpus.py` — not a live endpoint.

### Red-teaming (`RED_TEAMING.md` + `backend/tests/test_red_team.py`)

Doc covering: prompt injection via uploaded documents, jailbreaks to bypass the legal-advice disclaimer, PII extraction attempts, citation-hallucination probes, denial-of-wallet via repeated expensive queries, budget/rate-limit bypass attempts — each with current mitigation and known residual gaps (no real auth yet, so per-session throttling is bypassable by rotating `session_id`; heuristic PII/injection detection will have false negatives). A handful of these become actual adversarial pytest cases.

### Config & dependencies

`config.py` grows ~20 settings (model pair, per-model RPM/TPM limits, concurrency cap, per-user limit, breaker thresholds, backoff params, budgets, cache threshold/TTL, memory turns/TTL, Langfuse keys). `requirements.txt` adds `ragas`, `langchain-groq`, `langfuse`, `tenacity`. `.env.example` and `README.md` updated accordingly.

## Build order (checkpointed, same pattern as Phase 1)

1. Config additions + LLM Gateway (concurrency, dual token bucket, pre-flight estimate, per-user throttle, backoff+jitter, circuit breaker, fallback) + pricing + cost/budget tracking + `/usage` — the most explicitly-requested piece, built and verified first.
2. Guardrails (PII, injection, grounding, disclaimer) wired into the graph, response schema extended.
3. Semantic cache + conversation memory + graph rewiring with the conditional cache-hit edge.
4. HITL escalation queue + endpoints.
5. Langfuse tracing instrumentation.
6. Ragas evals (dataset + runner).
7. Red-teaming doc + adversarial tests.
8. Docs pass (README, .env.example) + full Docker Compose re-verification (rebuild, re-run full pytest suite, manual curl checks: repeat-question cache hit, `/usage` totals, response fields).

Existing patterns to reuse rather than reinvent: `redis.commands.search` usage from `backend/app/vectorstore/redis_store.py` (same approach for the semantic-cache index), the `@lru_cache` singleton-getter pattern used throughout (`get_settings`, `get_embedder`, `get_vector_store`, etc.), and the chars/4 token-approximation already established in `backend/app/ingestion/chunking.py`.

## Verification

1. Rebuild and restart the Docker Compose stack; confirm `/health` still OK.
2. Full pytest suite (existing e2e tests + new budget/circuit-breaker/red-team tests) green.
3. Manual: same question twice via `/query` → second call shows `cache_hit: true`, no added token/cost usage.
4. `GET /usage` reflects accurate cumulative tokens/cost; artificially low test budget triggers a clean rejection before any Groq call is made.
5. Simulate repeated Groq failures (monkeypatch) → circuit breaker opens → gateway transparently falls back to the other model.
6. `python -m app.evals.run_ragas` produces a scored report against the seeded corpus.
7. If the user supplies Langfuse keys, confirm a trace appears in their dashboard; otherwise confirm the app runs identically with tracing disabled.