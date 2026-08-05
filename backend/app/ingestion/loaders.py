import io
from pathlib import Path

from pypdf import PdfReader

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
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
