"""Bulk-seeds the vector store with real, full-text Indian case law scraped
from Indian Kanoon (indiankanoon.org).

Indian Kanoon has no free bulk-download API - their API is a paid product
for commercial use - so this works the way a well-behaved search-engine
crawler would: it uses the public search endpoint to collect candidate
judgment URLs across a spread of legal topics, then fetches each judgment
page directly. robots.txt (checked against a generic User-Agent) disallows
only a specific list of individual takedown'd documents, not /doc/ or
/search/ generally, but this is still scraping a live application - keep
--delay reasonable and don't run this against every topic on every court in
a tight loop.

Usage:
    python -m app.ingestion.bulk_seed_indiankanoon
    python -m app.ingestion.bulk_seed_indiankanoon --queries "bail,contempt of court" --limit 50
"""

import argparse
import html
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from app.ingestion.service import ingest_text

BASE_URL = "https://indiankanoon.org"
USER_AGENT = "Mozilla/5.0 (legal-rag-assistant research scraper; contact: local dev project)"
DEFAULT_DELAY_SECONDS = 1.5
DEFAULT_MIN_CHARS = 1500

DEFAULT_QUERIES = [
    "right to life personal liberty",
    "right to counsel legal aid",
    "anticipatory bail",
    "bail application sessions court",
    "freedom of speech expression",
    "fundamental rights article 32",
    "constitutional validity of statute",
    "service law wrongful termination",
    "contempt of court",
    "criminal appeal conviction sentence",
    "habeas corpus illegal detention",
    "right to equality article 14",
    "reservation policy backward classes",
    "environmental law pollution",
    "property rights acquisition",
    "matrimonial dispute maintenance",
    "consumer protection deficiency service",
    "arbitration award enforcement",
    "land acquisition compensation",
    "employment dispute industrial tribunal",
]


class _DivTextExtractor(HTMLParser):
    """Extracts all text inside the first <div class="{target_class}">,
    tracking div nesting depth since Indian Kanoon's markup has no other
    reliable end marker for where the judgment body div closes."""

    def __init__(self, target_class: str) -> None:
        super().__init__()
        self.target_class = target_class
        self.depth: int | None = None
        self.div_depth = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "div":
            return
        self.div_depth += 1
        if self.depth is None and dict(attrs).get("class") == self.target_class:
            self.depth = self.div_depth

    def handle_endtag(self, tag: str) -> None:
        if tag != "div":
            return
        if self.depth is not None and self.div_depth == self.depth:
            self.depth = None
        self.div_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth is not None:
            self.chunks.append(data)


def _extract_div_text(html: str, css_class: str) -> str:
    parser = _DivTextExtractor(css_class)
    parser.feed(html)
    return "".join(parser.chunks)


def _fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _search_doc_ids(query: str, pages: int) -> list[str]:
    ids: list[str] = []
    for page in range(pages):
        url = f"{BASE_URL}/search/?formInput={urllib.parse.quote(query)}%20doctypes%3Asupremecourt&pagenum={page}"
        try:
            html = _fetch(url)
        except Exception as exc:  # noqa: BLE001
            print(f"    search page {page} failed: {exc}")
            continue
        ids.extend(re.findall(r"/doc/(\d+)/", html))
        time.sleep(DEFAULT_DELAY_SECONDS)
    # de-duplicate while preserving order
    seen: set[str] = set()
    unique_ids = []
    for doc_id in ids:
        if doc_id not in seen:
            seen.add(doc_id)
            unique_ids.append(doc_id)
    return unique_ids


def _fetch_case(doc_id: str) -> tuple[str, str] | None:
    page_html = _fetch(f"{BASE_URL}/doc/{doc_id}/")
    title_match = re.search(r'<h2 class="doc_title">(.*?)</h2>', page_html, re.S)
    if not title_match:
        return None
    title = re.sub(r"<.*?>", "", title_match.group(1)).strip()
    title = re.sub(r"\s+on\s+\d+\s+\w+,?\s+\d{4}$", "", title)  # strip trailing "on 22 April, 1966"
    title = html.unescape(title)

    body = _extract_div_text(page_html, "judgments")
    body = html.unescape(body)
    body = re.sub(r"\[Cites \d+, Cited by \d+\]", "", body)
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    # A handful of judgments (large constitution-bench rulings with many
    # separate concurring/dissenting opinions) run past a million characters
    # and can otherwise dominate a whole batch's embedding time - cap at a
    # paragraph boundary rather than skip them outright.
    max_chars = 300_000
    if len(body) > max_chars:
        truncated = body[:max_chars]
        last_break = truncated.rfind("\n\n")
        if last_break > max_chars * 0.8:
            truncated = truncated[:last_break]
        body = truncated + "\n\n[Excerpt truncated - full text available at indiankanoon.org]"

    return title, body


def main() -> None:
    global DEFAULT_DELAY_SECONDS
    sys.stdout.reconfigure(line_buffering=True)  # visible progress when stdout is redirected to a file

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--queries",
        default=",".join(DEFAULT_QUERIES),
        help="Comma-separated search topics.",
    )
    parser.add_argument("--pages-per-query", type=int, default=2, help="Search result pages per topic (10 results/page).")
    parser.add_argument("--min-chars", type=int, default=DEFAULT_MIN_CHARS, help="Skip judgments shorter than this.")
    parser.add_argument("--limit", type=int, default=None, help="Stop after ingesting this many cases total.")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS, help="Seconds to wait between page fetches.")
    args = parser.parse_args()

    DEFAULT_DELAY_SECONDS = args.delay

    queries = [q.strip() for q in args.queries.split(",") if q.strip()]
    all_doc_ids: list[str] = []
    seen_ids: set[str] = set()

    for query in queries:
        print(f"\n=== Searching: {query} ===")
        ids = _search_doc_ids(query, args.pages_per_query)
        new_ids = [i for i in ids if i not in seen_ids]
        seen_ids.update(new_ids)
        all_doc_ids.extend(new_ids)
        print(f"  {len(new_ids)} new candidate documents ({len(all_doc_ids)} total so far)")

    print(f"\n{len(all_doc_ids)} unique candidate documents to fetch.\n")

    total_ingested = 0
    total_chunks = 0
    for doc_id in all_doc_ids:
        if args.limit is not None and total_ingested >= args.limit:
            print(f"\nReached --limit {args.limit}, stopping.")
            break

        try:
            result = _fetch_case(doc_id)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{doc_id}] fetch failed: {exc}")
            time.sleep(DEFAULT_DELAY_SECONDS)
            continue

        time.sleep(DEFAULT_DELAY_SECONDS)

        if result is None:
            continue
        title, body = result
        if len(body) < args.min_chars:
            continue

        try:
            ingest_result = ingest_text(source_title=title, text=body, doc_id=f"indiankanoon-{doc_id}")
        except ValueError:
            continue

        total_ingested += 1
        total_chunks += ingest_result.num_chunks
        print(f"  [{total_ingested}] {title} -> {ingest_result.num_chunks} chunks")

    print(f"\nDone. Ingested {total_ingested} cases, {total_chunks} chunks total.")


if __name__ == "__main__":
    main()
