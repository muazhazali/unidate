"""Download calendars, extract with Docling, and create validated review proposals."""
from __future__ import annotations

import argparse, hashlib, json, sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ollama_cloud import OllamaCloudClient

DATA, PROPOSALS, RAW = ROOT / "data", ROOT / "data/proposals", ROOT / "data/raw"
STATE_FILE = DATA / "source_state.json"
USER_AGENT = "UniDate/0.2 (+https://github.com/muazhazali/unidate)"

def read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

def discover_document(source: dict, response: httpx.Response, client: httpx.Client) -> tuple[str, bytes, str]:
    # A document_url may be retained purely as provenance for an HTML-first
    # source. Only resolve it when the source is explicitly configured for PDF
    # extraction; otherwise the registry page remains the parsed document.
    if source.get("document_url") and source.get("format") == "pdf":
        document = client.get(source["document_url"]); document.raise_for_status()
        return str(document.url), document.content, document.headers.get("content-type", "")
    content_type = response.headers.get("content-type", "")
    if source["parser"] != "linked_pdf" or "html" not in content_type:
        return str(response.url), response.content, content_type
    soup, session = BeautifulSoup(response.text, "html.parser"), source["academic_session"]
    links = [urljoin(str(response.url), a["href"]) for a in soup.find_all("a", href=True)
             if session in " ".join(a.stripped_strings) or session.replace("/", "-") in a["href"] or session.replace("/", "_") in a["href"]]
    if not links:
        return str(response.url), response.content, content_type
    document = client.get(links[0]); document.raise_for_status()
    return str(document.url), document.content, document.headers.get("content-type", "")

def save_raw_source(source: dict, *, final_url: str, content: bytes, content_type: str, digest: str, downloaded_at: datetime) -> Path:
    extension = ".pdf" if content.startswith(b"%PDF") or "pdf" in content_type or final_url.casefold().endswith(".pdf") else ".html"
    directory = RAW / source["university_code"] / source["academic_session"].replace("/", "-")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{source['id']}{extension}"; path.write_bytes(content)
    write_json(directory / f"{source['id']}.metadata.json", {
        "source_id": source["id"], "university_code": source["university_code"], "academic_session": source["academic_session"],
        "title": source["title"], "registry_url": source["url"], "resolved_url": final_url, "content_type": content_type,
        "content_hash": digest, "downloaded_at": downloaded_at.isoformat(), "filename": path.name, "bytes": len(content)})
    return path

def extract_pdf_with_docling(path: Path) -> dict:
    """Return only Docling-derived structured content; there is no pypdf fallback."""
    from docling.document_converter import DocumentConverter
    exported = DocumentConverter().convert(path).document.export_to_dict()
    pages: dict[int, list[dict]] = {}
    for item in [*exported.get("texts", []), *exported.get("tables", [])]:
        page = next((p.get("page_no") for p in item.get("prov", []) if p.get("page_no")), None)
        if page is not None:
            pages.setdefault(page, []).append({k: item[k] for k in ("label", "text", "data") if k in item})
    return {"extractor": "docling", "pages": [{"page": page, "items": items} for page, items in sorted(pages.items())]}

def extract_html(content: bytes, url: str, academic_session: str | None = None) -> dict:
    soup = BeautifulSoup(content, "html.parser")
    for unwanted in soup(["script", "style", "noscript", "svg"]): unwanted.decompose()
    main = soup.select_one("main, article, .item-page, #content") or soup.body or soup
    if academic_session:
        heading = main.find(attrs={"aria-label": lambda value: value and academic_session in value})
        panel = heading.find_parent("div", class_=lambda value: value and "sppb-panel" in value) if heading else None
        if panel:
            main = panel
    rows = []
    for element in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "tr", "a"]):
        text = " ".join(element.stripped_strings)
        if text:
            row = {"tag": element.name, "text": text}
            if element.name == "a" and element.get("href"): row["href"] = urljoin(url, element["href"])
            rows.append(row)
    return {"extractor": "beautifulsoup-html", "url": url, "elements": list({json.dumps(r, sort_keys=True): r for r in rows}.values())}

def build_proposal(source: dict, *, final_url: str, digest: str, previous: str | None, detected_at: datetime, document: dict, normalizer) -> dict:
    events, seen = [], set()
    for item in normalizer.normalize(document=document, source=source).events:
        key = (item.title, item.start_date, item.end_date, item.semester, item.audience)
        if key in seen: continue
        seen.add(key)
        event = item.model_dump(mode="json")
        event.update({"university_code": source["university_code"], "academic_session": source["academic_session"], "source_url": final_url, "review_status": "needs_review"})
        events.append(event)
    return {"schema_version": 2, "source_id": source["id"], "university_code": source["university_code"],
            "academic_session": source["academic_session"], "source_title": source["title"], "source_url": final_url,
            "previous_content_hash": previous, "content_hash": digest, "detected_at": detected_at.isoformat(),
            "status": "needs_review", "extraction": document["extractor"], "candidate_events": events}

def run(*, universities=None, download_only=False, extract_only=False, force=False, client=None, normalizer=None) -> tuple[int, int]:
    sources, state = read_json(DATA / "sources.json", []), read_json(STATE_FILE, {})
    if universities:
        selected = {c.casefold() for c in universities}; sources = [s for s in sources if s["university_code"].casefold() in selected]
    changed, failures, now = 0, [], datetime.now(UTC); PROPOSALS.mkdir(parents=True, exist_ok=True)
    own_client = client is None
    client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=60)
    try:
        for source in sources:
            try:
                response = client.get(source["url"]); response.raise_for_status()
                final_url, content, content_type = discover_document(source, response, client)
                digest = hashlib.sha256(content).hexdigest()
                raw_path = save_raw_source(source, final_url=final_url, content=content, content_type=content_type, digest=digest, downloaded_at=now)
                print(f"saved {source['id']}: {raw_path.relative_to(ROOT)}")
                if download_only: continue
                previous = state.get(source["id"], {}).get("content_hash")
                if previous == digest and not force: print(f"unchanged {source['id']}"); continue
                document = extract_pdf_with_docling(raw_path) if raw_path.suffix == ".pdf" else extract_html(content, final_url, source["academic_session"])
                extracted_path = raw_path.with_suffix(".docling.json" if raw_path.suffix == ".pdf" else ".html.json"); write_json(extracted_path, document)
                if extract_only: print(f"extracted {source['id']}: {extracted_path.relative_to(ROOT)}"); continue
                active_normalizer = normalizer or OllamaCloudClient()
                proposal = build_proposal(source, final_url=final_url, digest=digest, previous=previous, detected_at=now, document=document, normalizer=active_normalizer)
                write_json(PROPOSALS / f"{now.date().isoformat()}-{source['id']}.json", proposal)
                state[source["id"]] = {"content_hash": digest, "checked_at": now.isoformat(), "resolved_url": final_url, "status": "ok"}
                print(f"proposed {source['id']}: {len(proposal['candidate_events'])} complete events"); changed += 1
            except Exception as error:
                failures.append(f"{source['id']}: {error}"); print(f"failed {source['id']}: {error}", file=sys.stderr)
    finally:
        if own_client: client.close()
    if not download_only and not extract_only: write_json(STATE_FILE, state)
    print(f"complete: {changed} changed, {len(failures)} failed")
    return changed, len(failures)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-only", action="store_true"); parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--force", action="store_true"); parser.add_argument("--university", action="append")
    args = parser.parse_args()
    if args.download_only and args.extract_only: parser.error("--download-only and --extract-only cannot be combined")
    _, failures = run(universities=args.university, download_only=args.download_only, extract_only=args.extract_only, force=args.force)
    return 1 if failures else 0

if __name__ == "__main__": raise SystemExit(main())
