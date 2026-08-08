import io
from pathlib import Path

from pypdf import PdfReader

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        # "layout" mode uses each glyph's real position to reconstruct
        # spacing/columns; the default "plain" mode concatenates the raw
        # text-show operators in order, which silently drops word-boundary
        # spaces on multi-column/dense layouts (e.g. two-column resumes) -
        # "onLlama-3-8BusingUnsloth" instead of "on Llama-3-8B using Unsloth".
        pages = [
            page.extract_text(extraction_mode="layout") or "" for page in reader.pages
        ]
        text = "\n\n".join(pages)
    elif suffix in (".txt", ".md"):
        text = content.decode("utf-8", errors="replace")
    else:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Supported: {sorted(SUPPORTED_SUFFIXES)}"
        )

    text = text.strip()
    if not text:
        raise ValueError(f"No extractable text found in '{filename}'")
    return text
