from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.hitl.escalation import get_escalation_queue

router = APIRouter()


class ResolveRequest(BaseModel):
    notes: str = ""


@router.get("/escalations")
def list_escalations() -> list[dict]:
    return get_escalation_queue().list_pending()


@router.post("/escalations/{escalation_id}/resolve")
def resolve_escalation(escalation_id: str, request: ResolveRequest) -> dict:
    record = get_escalation_queue().resolve(escalation_id, request.notes)
    if record is None:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return record
