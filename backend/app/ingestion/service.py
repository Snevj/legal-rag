import uuid
from pathlib import Path

from app.config import get_settings
from app.embeddings.embedder import get_embedder
from app.ingestion.chunking import chunk_document
from app.ingestion.loaders import extract_text
from app.models.schemas import IngestResponse
from app.vectorstore.redis_store import get_vector_store


def ingest_text(source_title: str, text: str, doc_id: str | None = None) -> IngestResponse:
    settings = get_settings()
    doc_id = doc_id or uuid.uuid4().hex

    chunks = chunk_document(
        doc_id=doc_id,
        source_title=source_title,
        text=text,
        chunk_size_tokens=settings.chunk_size_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
    )
    if not chunks:
        raise ValueError(f"Document '{source_title}' produced no chunks")

    embedder = get_embedder()
    vectors = embedder.embed_documents([c.text for c in chunks])

    store = get_vector_store()
    store.upsert_chunks(
        [
            {
                "doc_id": c.doc_id,
                "source_title": c.source_title,
                "chunk_index": c.chunk_index,
                "text": c.text,
            }
            for c in chunks
        ],
        vectors,
    )

    return IngestResponse(doc_id=doc_id, source_title=source_title, num_chunks=len(chunks))


def ingest_file(filename: str, content: bytes) -> IngestResponse:
    text = extract_text(filename, content)
    source_title = Path(filename).stem.replace("_", " ").replace("-", " ").strip() or filename
    return ingest_text(source_title=source_title, text=text)
