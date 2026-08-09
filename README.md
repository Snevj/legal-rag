# Indian Legal RAG Assistant — Phase 3

A RAG pipeline for Indian legal Q&A: upload case law / legal documents, ask questions,
get answers grounded in and cited to the retrieved source text — indexed against real
Supreme Court of India judgments.

**Phase 1** shipped a working `retrieve → rerank → generate` pipeline. **Phase 2**
added production hardening: guardrails, cost/rate governance, semantic caching,
conversation memory, human-in-the-loop escalation, tracing, and evals. **Phase 3**
(current) adds a Next.js frontend — a chat-style research UI with a live technical
panel exposing routing, cost, latency, and guardrail telemetry for every answer,
plus admin views for `/usage` and `/escalations`. Cloud deployment is Phase 4.

## Stack

- **API**: FastAPI
- **Orchestration**: LangGraph (`route → cache_lookup → memory_load → input_guardrail
  → retrieve → rerank → generate → output_guardrail → escalation → memory_store →
  cache_store` graph)
- **Vector DB**: Redis Stack (RediSearch vector similarity) — also backs the
  semantic answer cache, conversation memory, token buckets, and escalation queue
- **Embeddings**: `BAAI/bge-small-en-v1.5` (local, via `sentence-transformers`)
- **Reranker**: `BAAI/bge-reranker-base` (local cross-encoder)
- **LLM**: Groq, cheap/expensive model routing by question difficulty
  (`llama-3.1-8b-instant` / `llama-3.3-70b-versatile`), behind a resilience gateway
  (concurrency limiting, dual RPM/TPM token buckets, per-session throttling,
  exponential backoff, circuit breaker, in-Groq model fallback)
- **Guardrails**: PII detection, prompt-injection detection, citation/grounding
  verification, not-legal-advice disclaimer enforcement
- **Cost governance**: pre-flight token estimation + global/per-session daily
  budgets (`backend/app/cost/budget.py`), `GET /usage`
- **Tracing**: Langfuse (optional, no-ops if unconfigured)
- **Evals**: Ragas-style LLM-judge metrics against the seeded corpus
  (`backend/app/evals/`)
- **Red-teaming**: see [`RED_TEAMING.md`](RED_TEAMING.md) for adversarial scenarios,
  mitigations, and known gaps
- **Frontend**: Next.js (App Router) + Tailwind v4 + shadcn/ui, dark-only theme
  adapted from the [Mercury](https://mercury.com) design system
  ([`frontend/DESIGN.md`](frontend/DESIGN.md)) — chat-style Q&A with a live
  technical/debug panel, plus `/usage` and `/escalations` admin pages

## Setup

1. Get a free API key at [console.groq.com](https://console.groq.com).
2. Copy `.env.example` to `.env` and fill in `GROQ_API_KEY`. Everything else has a
   working default; `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` (tracing) and
   `ADMIN_API_KEY` (protects `/escalations` and `/usage`) are optional.
3. Start everything:

   ```bash
   docker compose up -d --build
   ```

   First build downloads the embedding/reranker models — expect it to take a
   few minutes.

4. Seed the vector store with the bundled public-domain case law (5 landmark
   Supreme Court of India judgments, used by the tests/evals):

   ```bash
   docker compose exec backend python -m app.ingestion.seed_corpus
   ```

   Optionally, bulk-seed hundreds more real, full-text Indian Supreme Court
   judgments scraped from [Indian Kanoon](https://indiankanoon.org) (no
   bulk-download API exists — Indian Kanoon's API is a paid commercial
   product — so this crawls the public site directly, at a deliberately
   modest rate):

   ```bash
   docker compose exec backend python -m app.ingestion.bulk_seed_indiankanoon
   # or a narrower/faster run:
   docker compose exec backend python -m app.ingestion.bulk_seed_indiankanoon \
     --queries "bail,contempt of court" --limit 50
   ```

   This is what makes retrieval meaningfully different from just pasting a
   document into a chat model — a corpus of hundreds of judgments doesn't
   fit in any context window, so retrieval is doing real work instead of
   being a novelty. `--min-chars` (default 1500) filters out very short
   orders so the corpus stays useful rather than noisy.

   (`backend/app/ingestion/bulk_seed_caselaw.py` also still exists — it
   bulk-seeds U.S. Reports opinions from Harvard's Caselaw Access Project,
   left over from before this project's India-specific pivot. Not part of
   the default setup.)

5. Ask a question:

   ```bash
   curl -X POST localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{"question": "What guidelines did the Court lay down in Vishaka v. State of Rajasthan?"}'
   ```

6. Upload your own document:

   ```bash
   curl -X POST localhost:8000/ingest -F "file=@/path/to/document.pdf"
   ```

7. Check cumulative token/cost usage:

   ```bash
   curl localhost:8000/usage
   ```

8. Review escalated answers (flagged by a guardrail, e.g. PII, ungrounded citation,
   prompt injection, or an explicit `request_human_review` on the query):

   ```bash
   curl localhost:8000/escalations
   curl -X POST localhost:8000/escalations/<id>/resolve -d '{"notes": "reviewed"}'
   ```

   If `ADMIN_API_KEY` is set, pass it as `-H "X-API-Key: ..."` on both `/escalations`
   and `/usage`.

9. Run the frontend:

   ```bash
   cd frontend
   cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL, defaults to localhost:8000
   npm install
   npm run dev
   ```

   Open [localhost:3000](http://localhost:3000) — ask questions, upload documents
   (paperclip icon), and click any answer bubble to inspect its full technical
   detail (routing, cost, latency, guardrail flags, sources) in the side panel.
   `/usage` and `/escalations` mirror the backend admin endpoints, with an
   optional `ADMIN_API_KEY` field if the backend requires one.

## Running tests

```bash
cd backend
pip install -r requirements.txt
GROQ_API_KEY=... REDIS_URL=redis://localhost:6379 pytest tests/ -v
```

(Requires Redis running — `docker compose up -d redis`. Most tests fake the LLM
gateway via `conftest.py`; `test_query_e2e.py` and the Ragas-judge tests in
`test_ragas_red_team.py` call the real Groq API and need a real key.)

Run the eval suite against the seeded corpus:

```bash
cd backend
python -m app.evals.run_evals          # real Groq calls, needs GROQ_API_KEY
EVAL_DRY_RUN=1 python -m app.evals.run_evals   # deterministic, no API calls (used in CI)
```

## Roadmap

- **Phase 1** (done): retrieve → rerank → generate pipeline, FastAPI, Redis Stack,
  local embeddings/reranker, Groq generation.
- **Phase 2** (done): citation/grounding guardrails, PII detection, disclaimer
  enforcement, prompt-injection detection, LLM resilience gateway (concurrency
  limit, dual token buckets, per-session throttling, backoff, circuit breaker,
  in-Groq fallback), cost/budget tracking, Redis semantic caching, conversation
  memory, cheap/expensive model routing, human-in-the-loop escalation, Langfuse
  tracing, Ragas-style evals, red-teaming notes (see [`RED_TEAMING.md`](RED_TEAMING.md)
  for the known gaps carried forward, principally: no authentication yet, so
  per-session budgets/throttling are only as strong as the client's honesty about
  `session_id`, and `/escalations`/`/usage` are unauthenticated unless
  `ADMIN_API_KEY` is set).
- **Phase 3** (done): Next.js + Tailwind + shadcn/ui frontend — chat UI, technical
  telemetry panel, `/usage` and `/escalations` admin views.
- **Phase 4**: Docker Compose hardening + AWS free-tier deployment (EC2 + S3) —
  the frontend isn't containerized yet, this lands with the rest of the
  deployment hardening.

## Disclaimer

This tool assists with legal research. It does not provide legal advice and
its output should always be independently verified against primary sources.
