import re
from dataclasses import dataclass

# Priority order for splitting: prefer breaking on structural boundaries that
# actually occur in legal documents (section breaks, paragraphs) before
# falling back to sentence/word boundaries. This keeps citations, numbered
# holdings, and paragraph-scoped reasoning intact within a single chunk far
# more often than fixed-size chunking would.
LEGAL_SEPARATORS = ["\n\n\n", "\n\n", "\n", ". ", " ", ""]

# Rough chars-per-token ratio for English legal prose; avoids pulling in a
# tokenizer dependency just to size chunks.
CHARS_PER_TOKEN = 4


@dataclass
class DocumentChunk:
    doc_id: str
    source_title: str
    chunk_index: int
    text: str


def _recursive_split(text: str, chunk_size: int, separators: list[str]) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    sep, remaining = separators[0], separators[1:]
    pieces = list(text) if sep == "" else text.split(sep)

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = current + (sep if current else "") + piece
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)

        if len(piece) > chunk_size and remaining:
            chunks.extend(_recursive_split(piece, chunk_size, remaining))
            current = ""
        else:
            current = piece

    if current.strip():
        chunks.append(current)

    return chunks


def chunk_text(text: str, chunk_size_tokens: int, overlap_tokens: int) -> list[str]:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n\n", text)

    chunk_size = chunk_size_tokens * CHARS_PER_TOKEN
    overlap = overlap_tokens * CHARS_PER_TOKEN

    raw_chunks = _recursive_split(text, chunk_size, LEGAL_SEPARATORS)
    raw_chunks = [c.strip() for c in raw_chunks if c.strip()]

    if overlap <= 0 or len(raw_chunks) <= 1:
        return raw_chunks

    overlapped = [raw_chunks[0]]
    for i in range(1, len(raw_chunks)):
        prefix = raw_chunks[i - 1][-overlap:]
        overlapped.append(f"{prefix} {raw_chunks[i]}".strip())
    return overlapped


def chunk_document(
    doc_id: str,
    source_title: str,
    text: str,
    chunk_size_tokens: int,
    overlap_tokens: int,
) -> list[DocumentChunk]:
    pieces = chunk_text(text, chunk_size_tokens, overlap_tokens)
    return [
        DocumentChunk(doc_id=doc_id, source_title=source_title, chunk_index=i, text=piece)
        for i, piece in enumerate(pieces)
    ]
