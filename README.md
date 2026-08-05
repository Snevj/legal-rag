# Legal RAG Assistant — Phase 1

A RAG pipeline for legal Q&A: upload case law / legal documents, ask questions, get
answers grounded in and cited to the retrieved source text.

This is **Phase 1**: a working `retrieve → rerank → generate` pipeline behind a
FastAPI backend, using Redis Stack as the vector store, local embedding/reranking
models (no API cost), and Groq for generation. No frontend, guardrails, evals,
tracing, caching, or model routing yet — those land in later phases.

## Stack

- **API**: FastAPI
- **Orchestration**: LangGraph (`retrieve → rerank → generate` graph)
- **Vector DB**: Redis Stack (RediSearch vector similarity)
- **Embeddings**: `BAAI/bge-small-en-v1.5` (local, via `sentence-transformers`)
- **Reranker**: `BAAI/bge-reranker-base` (local cross-encoder)
- **LLM**: Groq (`llama-3.3-70b-versatile`)

## Setup

1. Get a free API key at [console.groq.com](https://console.groq.com).
2. Copy `.env.example` to `.env` and fill in `GROQ_API_KEY`.
3. Start everything:

   ```bash
   docker compose up -d --build
   ```

   First build downloads the embedding/reranker models — expect it to take a
   few minutes.

4. Seed the vector store with the bundled public-domain case law:

   ```bash
   docker compose exec backend python -m app.ingestion.seed_corpus
   ```

5. Ask a question:

   ```bash
   curl -X POST localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{"question": "What did the Court hold about the right to counsel in Miranda v. Arizona?"}'
   ```

6. Upload your own document:

   ```bash
   curl -X POST localhost:8000/ingest -F "file=@/path/to/document.pdf"
   ```

## Running tests

```bash
cd backend
pip install -r requirements.txt
GROQ_API_KEY=... REDIS_URL=redis://localhost:6379 pytest tests/ -v
```

(Requires Redis running — `docker compose up -d redis` — and a real Groq key,
since Phase 1 has no mocking layer yet.)

## Roadmap

- **Phase 2**: citation/grounding guardrails, PII redaction, UPL disclaimers,
  Ragas evals, Langfuse tracing, Redis semantic caching, cheap/expensive model
  routing, human-in-the-loop escalation, agent memory, red-teaming notes.
- **Phase 3**: Next.js + Tailwind + shadcn/ui frontend.
- **Phase 4**: Docker Compose hardening + AWS free-tier deployment (EC2 + S3).

## Disclaimer

This tool assists with legal research. It does not provide legal advice and
its output should always be independently verified against primary sources.
