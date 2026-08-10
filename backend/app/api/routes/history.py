from fastapi import APIRouter

from app.memory.chat_history import get_chat_history
from app.models.schemas import ChatHistoryTurn

router = APIRouter()


@router.get("/history", response_model=list[ChatHistoryTurn])
def history(session_id: str) -> list[ChatHistoryTurn]:
    return [ChatHistoryTurn(**turn) for turn in get_chat_history().load(session_id)]
