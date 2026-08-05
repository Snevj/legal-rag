from fastapi import APIRouter

from app.cost.budget import get_budget_tracker
from app.models.schemas import UsageResponse

router = APIRouter()


@router.get("/usage", response_model=UsageResponse)
def usage(session_id: str | None = None) -> UsageResponse:
    tracker = get_budget_tracker()
    return UsageResponse(**tracker.get_usage(session_id))
