from pathlib import Path

from app.config import get_settings
from app.ingestion.service import ingest_text


def main() -> None:
    settings = get_settings()
    corpus_dir = Path(settings.seed_corpus_dir)
    if not corpus_dir.is_absolute():
        corpus_dir = Path.cwd() / corpus_dir

    files = sorted(corpus_dir.glob("*.txt"))
    if not files:
        print(f"No seed files found in {corpus_dir}")
        return

    for path in files:
        text = path.read_text(encoding="utf-8")
        title_line = text.splitlines()[0].strip()
        doc_id = path.stem
        print(f"Ingesting {title_line} ({path.name})...")
        result = ingest_text(source_title=title_line, text=text, doc_id=doc_id)
        print(f"  -> {result.num_chunks} chunks")


if __name__ == "__main__":
    main()
