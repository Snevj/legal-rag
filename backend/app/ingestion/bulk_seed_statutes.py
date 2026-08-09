"""Seeds the vector store with real, full statute text (bare Acts) from
Indian Kanoon - the case-law corpus alone can't answer "what does Section X
say", only "what have courts said about it", which is a real gap for a
legal research tool. Acts are fetched by exact doc ID (curated list below,
found via one-off search) rather than by search-at-runtime, since act pages
are large and a bad search match would silently ingest the wrong act.

Usage:
    python -m app.ingestion.bulk_seed_statutes
    python -m app.ingestion.bulk_seed_statutes --acts constitution_of_india,indian_penal_code_1860
"""

import argparse
import html
import re

from app.ingestion.bulk_seed_indiankanoon import _extract_div_text, _fetch
from app.ingestion.service import ingest_text

MAX_CHARS = 300_000

# slug -> (Indian Kanoon doc ID, display title). Doc IDs found via Indian
# Kanoon search for each act's exact title, one-off, and pinned here rather
# than re-searched at runtime.
ACTS: dict[str, tuple[str, str]] = {
    "constitution_of_india": ("1218090", "The Constitution of India, 1950"),
    "indian_penal_code_1860": ("1569253", "The Indian Penal Code, 1860"),
    "code_of_criminal_procedure_1973": ("1922870", "The Code of Criminal Procedure, 1973"),
    "indian_evidence_act_1872": ("1436241", "The Indian Evidence Act, 1872"),
    "indian_contract_act_1872": ("1704043", "The Indian Contract Act, 1872"),
    "information_technology_act_2000": ("1965344", "The Information Technology Act, 2000"),
    "code_of_civil_procedure_1908": ("1199182", "The Code of Civil Procedure, 1908"),
    "right_to_information_act_2005": ("1360819", "The Right To Information Act, 2005"),
    "advocates_act_1961": ("1188742", "The Advocates Act, 1961"),
}


def _fetch_act(doc_id: str, title: str) -> str:
    page_html = _fetch(f"https://indiankanoon.org/doc/{doc_id}/")
    body = _extract_div_text(page_html, "maindoc")
    body = html.unescape(body)
    body = re.sub(r"\[Cites \d+, Cited by \d+\]", "", body)
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    if len(body) < 2000:
        raise ValueError(f"'{title}' (doc {doc_id}) extracted suspiciously short ({len(body)} chars) - check the doc ID/page template")

    if len(body) > MAX_CHARS:
        truncated = body[:MAX_CHARS]
        last_break = truncated.rfind("\n\n")
        if last_break > MAX_CHARS * 0.8:
            truncated = truncated[:last_break]
        body = truncated + "\n\n[Excerpt truncated - full text available at indiankanoon.org]"

    return f"{title}\n\n{body}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--acts",
        default=",".join(ACTS.keys()),
        help="Comma-separated act slugs (see ACTS dict in this file).",
    )
    args = parser.parse_args()

    slugs = [s.strip() for s in args.acts.split(",") if s.strip()]
    total_ingested = 0
    total_chunks = 0

    for slug in slugs:
        if slug not in ACTS:
            print(f"Unknown act slug '{slug}', skipping. Known: {list(ACTS)}")
            continue
        doc_id, title = ACTS[slug]
        print(f"Fetching {title} (doc {doc_id})...")
        try:
            text = _fetch_act(doc_id, title)
        except Exception as exc:  # noqa: BLE001
            print(f"  failed: {exc}")
            continue

        result = ingest_text(source_title=title, text=text, doc_id=f"statute-{slug}")
        total_ingested += 1
        total_chunks += result.num_chunks
        print(f"  -> {result.num_chunks} chunks")

    print(f"\nDone. Ingested {total_ingested} acts, {total_chunks} chunks total.")


if __name__ == "__main__":
    main()
