from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import escalations, health, history, ingest, query, usage
from app.tracing.langfuse_client import flush as flush_langfuse


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    flush_langfuse()


app = FastAPI(title="Legal RAG Assistant", version="0.1.0", lifespan=lifespan)

# Permissive for local dev so the Phase 3 frontend (different origin/port)
# can call this API without extra config. Tighten before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(ingest.router, tags=["ingestion"])
app.include_router(query.router, tags=["query"])
app.include_router(history.router, tags=["history"])
app.include_router(usage.router, tags=["usage"])
app.include_router(escalations.router, tags=["escalations"])
