from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.ingestion.service import ingest_file
from app.memory.session_uploads import get_session_uploads
from app.models.schemas import IngestResponse

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...), session_id: str | None = Form(None)) -> IngestResponse:
    content = await file.read()
    try:
        result = ingest_file(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if session_id:
        get_session_uploads().record(session_id, result.doc_id, result.source_title)

    return result
