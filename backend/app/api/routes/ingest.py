from fastapi import APIRouter, File, HTTPException, UploadFile

from app.ingestion.service import ingest_file
from app.models.schemas import IngestResponse

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...)) -> IngestResponse:
    content = await file.read()
    try:
        return ingest_file(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
