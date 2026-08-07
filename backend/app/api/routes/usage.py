from fastapi import APIRouter, Depends, Header, HTTPException

from app.cost.budget import get_budget_tracker
from app.models.schemas import UsageResponse
from app.config import get_settings

router = APIRouter()


def require_admin_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.admin_api_key:
        return
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/usage", response_model=UsageResponse)
def usage(session_id: str | None = None, admin: None = Depends(require_admin_api_key)) -> UsageResponse:
    tracker = get_budget_tracker()
    return UsageResponse(**tracker.get_usage(session_id))
