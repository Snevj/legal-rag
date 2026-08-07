from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from app.hitl.escalation import get_escalation_queue
from app.config import get_settings

router = APIRouter()


class ResolveRequest(BaseModel):
    notes: str = ""


def require_admin_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.admin_api_key:
        return
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/escalations")
def list_escalations(admin: None = Depends(require_admin_api_key)) -> list[dict]:
    return get_escalation_queue().list_pending()


@router.post("/escalations/{escalation_id}/resolve")
def resolve_escalation(escalation_id: str, request: ResolveRequest, admin: None = Depends(require_admin_api_key)) -> dict:
    record = get_escalation_queue().resolve(escalation_id, request.notes)
    if record is None:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return record
