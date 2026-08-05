from fastapi import APIRouter

from app.models.schemas import HealthResponse
from app.vectorstore.redis_store import get_vector_store

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    redis_connected = get_vector_store().ping()
    return HealthResponse(
        status="ok" if redis_connected else "degraded",
        redis_connected=redis_connected,
    )
