"""Check registered public calendar sources and prepare review proposals.

This script never changes approved events.json. Changed source content is saved as a
versioned proposal so a maintainer can verify candidates in the generated GitHub PR.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PROPOSALS = DATA / "proposals"
RAW = DATA / "raw"
STATE_FILE = DATA / "source_state.json"
USER_AGENT = "UniDate/0.1 (+https://github.com; public academic calendar checker)"

MONTHS = {
    "january": 1, "januari": 1, "february": 2, "februari": 2,
    "march": 3, "mac": 3, "april": 4, "may": 5, "mei": 5,
    "june": 6, "jun": 6, "july": 7, "julai": 7, "august": 8,
    "ogos": 8, "september": 9, "october": 10, "oktober": 10,
    "november": 11, "disember": 12, "december": 12,
}
MONTH_PATTERN = "|".join(sorted(MONTHS, key=len, reverse=True))
RANGE_PATTERNS = [
    re.compile(rf"(?P<d1>\d{{1,2}})\s+(?P<m1>{MONTH_PATTERN})\s+(?P<y1>20\d{{2}})\s*(?:-|–|—|to|hingga)\s*(?P<d2>\d{{1,2}})\s+(?P<m2>{MONTH_PATTERN})\s+(?P<y2>20\d{{2}})", re.I),
    re.compile(rf"(?P<d1>\d{{1,2}})\s+(?P<m1>{MONTH_PATTERN})\s*(?:-|–|—|to|hingga)\s*(?P<d2>\d{{1,2}})\s+(?P<m2>{MONTH_PATTERN})\s+(?P<y2>20\d{{2}})", re.I),
    re.compile(rf"(?P<d1>\d{{1,2}})\s*(?:-|–|—|to|hingga)\s*(?P<d2>\d{{1,2}})\s+(?P<m2>{MONTH_PATTERN})\s+(?P<y2>20\d{{2}})", re.I),
    re.compile(r"(?P<d1>\d{1,2})[./-](?P<m1>\d{1,2})[./-](?P<y1>20\d{2})\s*(?:-|–|—|to|hingga)\s*(?P<d2>\d{1,2})[./-](?P<m2>\d{1,2})[./-](?P<y2>20\d{2})", re.I),
]


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def discover_document(source: dict, response: httpx.Response, client: httpx.Client) -> tuple[str, bytes, str]:
    if source.get("document_url"):
        document = client.get(source["document_url"])
        document.raise_for_status()
        return str(document.url), document.content, document.headers.get("content-type", "")
    content_type = response.headers.get("content-type", "")
    if source["parser"] != "linked_pdf" or "html" not in content_type:
        return str(response.url), response.content, content_type

    soup = BeautifulSoup(response.text, "html.parser")
    session = source["academic_session"]
    links = []
    for anchor in soup.find_all("a", href=True):
        label = " ".join(anchor.stripped_strings)
        url = urljoin(str(response.url), anchor["href"])
        if session in label or session.replace("/", "_") in url or session.replace("/", "-") in url:
            links.append(url)
    if not links:
        return str(response.url), response.content, content_type
    document = client.get(links[0])
    document.raise_for_status()
    return str(document.url), document.content, document.headers.get("content-type", "")


def save_raw_source(
    source: dict,
    *,
    final_url: str,
    content: bytes,
    content_type: str,
    digest: str,
    downloaded_at: datetime,
) -> Path:
    if content.startswith(b"%PDF") or "pdf" in content_type or final_url.casefold().endswith(".pdf"):
        extension = ".pdf"
    elif "html" in content_type:
        extension = ".html"
    else:
        extension = ".bin"
    session = source["academic_session"].replace("/", "-")
    directory = RAW / source["university_code"] / session
    directory.mkdir(parents=True, exist_ok=True)
    document_path = directory / f"{source['id']}{extension}"
    document_path.write_bytes(content)
    write_json(
        directory / f"{source['id']}.metadata.json",
        {
            "source_id": source["id"],
            "university_code": source["university_code"],
            "academic_session": source["academic_session"],
            "title": source["title"],
            "registry_url": source["url"],
            "resolved_url": final_url,
            "content_type": content_type,
            "content_hash": digest,
            "downloaded_at": downloaded_at.isoformat(),
            "filename": document_path.name,
            "bytes": len(content),
        },
    )
    return document_path


def extract_text(content: bytes, content_type: str, url: str) -> tuple[str, list[dict]]:
    if "pdf" in content_type or url.casefold().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        pages = []
        text_parts = []
        for number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            pages.append({"page": number, "text": page_text})
            text_parts.append(page_text)
        return "\n".join(text_parts), pages
    soup = BeautifulSoup(content, "html.parser")
    for unwanted in soup(["script", "style", "noscript"]):
        unwanted.decompose()
    text = soup.get_text("\n", strip=True)
    return text, [{"page": None, "text": text}]


def month(value: str | None) -> int | None:
    if value is None:
        return None
    return int(value) if value.isdigit() else MONTHS[value.casefold()]


def parse_match(match: re.Match) -> tuple[str, str] | None:
    groups = match.groupdict()
    end_year = int(groups["y2"])
    end_month = month(groups["m2"])
    start_month = month(groups.get("m1")) or end_month
    start_year = int(groups.get("y1") or end_year)
    if start_month and end_month and start_year == end_year and start_month > end_month:
        start_year -= 1
    try:
        start = date(start_year, start_month, int(groups["d1"]))
        end = date(end_year, end_month, int(groups["d2"]))
    except (TypeError, ValueError):
        return None
    if end < start or (end - start).days > 370:
        return None
    return start.isoformat(), end.isoformat()


def extract_candidates(pages: list[dict], session: str) -> list[dict]:
    candidates = []
    seen = set()
    for page in pages:
        lines = [re.sub(r"\s+", " ", line).strip() for line in page["text"].splitlines() if line.strip()]
        for index, line in enumerate(lines):
            context = " | ".join(lines[max(0, index - 2) : min(len(lines), index + 3)])
            for pattern in RANGE_PATTERNS:
                for match in pattern.finditer(line):
                    parsed = parse_match(match)
                    if not parsed:
                        continue
                    start, end = parsed
                    if not ({session[:4], session[-4:]} & {start[:4], end[:4]}):
                        continue
                    key = (start, end, context)
                    if key in seen:
                        continue
                    seen.add(key)
                    candidates.append({
                        "start_date": start,
                        "end_date": end,
                        "source_page": page["page"],
                        "raw_context": context[:600],
                        "review_status": "needs_review",
                    })
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Save current source files without creating proposals or changing source state.",
    )
    parser.add_argument(
        "--university",
        action="append",
        help="Only process this university code; repeat to select multiple universities.",
    )
    args = parser.parse_args()
    sources = read_json(DATA / "sources.json", [])
    if args.university:
        selected = {code.casefold() for code in args.university}
        sources = [source for source in sources if source["university_code"].casefold() in selected]
    state = read_json(STATE_FILE, {})
    changed = 0
    failures = []
    now = datetime.now(UTC)
    PROPOSALS.mkdir(parents=True, exist_ok=True)

    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=45) as client:
        for source in sources:
            try:
                response = client.get(source["url"])
                response.raise_for_status()
                final_url, content, content_type = discover_document(source, response, client)
                digest = hashlib.sha256(content).hexdigest()
                raw_path = save_raw_source(
                    source,
                    final_url=final_url,
                    content=content,
                    content_type=content_type,
                    digest=digest,
                    downloaded_at=now,
                )
                print(f"saved {source['id']}: {raw_path.relative_to(ROOT)}")
                if args.download_only:
                    continue
                previous = state.get(source["id"], {}).get("content_hash")
                if previous == digest:
                    print(f"unchanged {source['id']}")
                    continue
                state[source["id"]] = {
                    "content_hash": digest,
                    "checked_at": now.isoformat(),
                    "resolved_url": final_url,
                    "status": "ok",
                }
                _, pages = extract_text(content, content_type, final_url)
                proposal = {
                    "schema_version": 1,
                    "source_id": source["id"],
                    "university_code": source["university_code"],
                    "academic_session": source["academic_session"],
                    "source_title": source["title"],
                    "source_url": final_url,
                    "previous_content_hash": previous,
                    "content_hash": digest,
                    "detected_at": now.isoformat(),
                    "status": "needs_review",
                    "candidate_events": extract_candidates(pages, source["academic_session"]),
                }
                filename = f"{now.date().isoformat()}-{source['id']}.json"
                write_json(PROPOSALS / filename, proposal)
                print(f"changed {source['id']}: {len(proposal['candidate_events'])} candidates")
                changed += 1
            except Exception as error:  # keep checking remaining independent sources
                failures.append(f"{source['id']}: {error}")
                print(f"failed {source['id']}: {error}", file=sys.stderr)

    if not args.download_only:
        write_json(STATE_FILE, state)
    print(f"complete: {changed} changed, {len(failures)} failed")
    return 1 if failures and len(failures) == len(sources) else 0


if __name__ == "__main__":
    raise SystemExit(main())
