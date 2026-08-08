"""Bulk-seeds the vector store with real, full-text U.S. case law from
Harvard's Caselaw Access Project static bulk data (static.case.law) - public
domain, no API key/signup required, unlike CourtListener's or GovInfo's
full-text endpoints which do require a free account.

Each U.S. Reports volume bundles every opinion filed in it, including
hundreds of one-line cert-denial orders with no substantive content - those
are filtered out via a minimum word count so the corpus stays useful for
retrieval instead of diluting it with noise.

Usage:
    python -m app.ingestion.bulk_seed_caselaw --volumes 300,320,340,350,370,384,395,410
    python -m app.ingestion.bulk_seed_caselaw --volumes 300-310
"""

import argparse
import io
import json
import urllib.request
import zipfile

from app.ingestion.service import ingest_text

BASE_URL = "https://static.case.law"
DEFAULT_MIN_WORDS = 300


def _parse_volumes(spec: str) -> list[int]:
    volumes: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            volumes.extend(range(int(start), int(end) + 1))
        elif part:
            volumes.append(int(part))
    return volumes


def _case_text(case: dict) -> str:
    head_matter = case.get("casebody", {}).get("head_matter", "")
    opinions = case.get("casebody", {}).get("opinions", [])
    body = "\n\n".join(op.get("text", "") for op in opinions)
    return f"{head_matter}\n\n{body}".strip()


def _fetch_volume_cases(reporter: str, volume: int) -> list[dict]:
    url = f"{BASE_URL}/{reporter}/{volume}.zip"
    # The S3-backed static host 403s the default urllib User-Agent.
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (legal-rag-assistant bulk-seed script)"})
    with urllib.request.urlopen(request) as resp:
        data = resp.read()

    cases = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            if not name.startswith("json/") or not name.endswith(".json"):
                continue
            cases.append(json.loads(zf.read(name)))
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--volumes",
        default="300,320,340,350,370,384,395,410",
        help="Comma-separated volume numbers and/or ranges (e.g. '300,320-325').",
    )
    parser.add_argument("--reporter", default="us", help="Reporter series slug (default: us = U.S. Reports).")
    parser.add_argument(
        "--min-words",
        type=int,
        default=DEFAULT_MIN_WORDS,
        help="Skip cases below this word count (filters out one-line cert-denial noise).",
    )
    parser.add_argument("--limit", type=int, default=None, help="Stop after ingesting this many cases total.")
    args = parser.parse_args()

    volumes = _parse_volumes(args.volumes)
    total_ingested = 0
    total_chunks = 0

    for volume in volumes:
        print(f"\n=== Volume {args.reporter} {volume} ===")
        try:
            cases = _fetch_volume_cases(args.reporter, volume)
        except Exception as exc:  # noqa: BLE001 - report and continue with remaining volumes
            print(f"  failed to download/parse: {exc}")
            continue

        kept = [c for c in cases if c.get("analysis", {}).get("word_count", 0) >= args.min_words]
        print(f"  {len(cases)} cases in volume, {len(kept)} pass the {args.min_words}-word filter")

        for case in kept:
            if args.limit is not None and total_ingested >= args.limit:
                print(f"\nReached --limit {args.limit}, stopping.")
                _print_summary(total_ingested, total_chunks)
                return

            text = _case_text(case)
            if not text.strip():
                continue

            title = case.get("name_abbreviation") or case.get("name") or f"case {case['id']}"
            doc_id = f"caselaw-{case['id']}"
            try:
                result = ingest_text(source_title=title, text=text, doc_id=doc_id)
            except ValueError:
                continue

            total_ingested += 1
            total_chunks += result.num_chunks
            print(f"  [{total_ingested}] {title} -> {result.num_chunks} chunks")

    _print_summary(total_ingested, total_chunks)


def _print_summary(total_ingested: int, total_chunks: int) -> None:
    print(f"\nDone. Ingested {total_ingested} cases, {total_chunks} chunks total.")


if __name__ == "__main__":
    main()
