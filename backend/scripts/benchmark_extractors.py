"""Compare pypdf and Docling against UniDate's manually verified events."""

from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path

from docling.document_converter import DocumentConverter
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUTPUT = RAW / "benchmarks"
EVENTS = json.loads((ROOT / "data" / "events.json").read_text(encoding="utf-8"))
PDFS = {
    "um": RAW / "um" / "2026-2027" / "um-bachelor-2026.pdf",
    "ukm": RAW / "ukm" / "2026-2027" / "ukm-main-2026.pdf",
}
MONTHS = {
    1: ("january", "januari"), 2: ("february", "februari"),
    3: ("march", "mac"), 4: ("april",), 5: ("may", "mei"),
    6: ("june", "jun"), 7: ("july", "julai"), 8: ("august", "ogos"),
    9: ("september",), 10: ("october", "oktober"),
    11: ("november",), 12: ("december", "disember"),
}


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def date_variants(value: str) -> set[str]:
    parsed = date.fromisoformat(value)
    variants = {
        normalized(value),
        normalized(parsed.strftime("%d.%m.%Y")),
        normalized(parsed.strftime("%d/%m/%Y")),
    }
    for month in MONTHS[parsed.month]:
        variants.add(normalized(f"{parsed.day} {month} {parsed.year}"))
        variants.add(normalized(f"{parsed.day:02d} {month} {parsed.year}"))
    return variants


def score(text: str, university: str) -> dict:
    compact = normalized(text)
    expected = [event for event in EVENTS if event["university_code"] == university]
    title_hits = 0
    date_hits = 0
    paired_hits = 0
    details = []
    for event in expected:
        title = normalized(event["title"])
        title_position = compact.find(title)
        title_found = title_position >= 0
        dates = date_variants(event["start_date"])
        if event.get("end_date"):
            dates |= date_variants(event["end_date"])
        found_date_positions = [compact.find(variant) for variant in dates if compact.find(variant) >= 0]
        date_found = bool(found_date_positions)
        paired = title_found and any(abs(position - title_position) <= 1200 for position in found_date_positions)
        title_hits += title_found
        date_hits += date_found
        paired_hits += paired
        details.append({
            "id": event["id"],
            "title_found": title_found,
            "date_found": date_found,
            "title_date_nearby": paired,
        })
    total = len(expected)
    return {
        "expected_events": total,
        "title_coverage": title_hits / total if total else 0,
        "date_coverage": date_hits / total if total else 0,
        "title_date_pair_coverage": paired_hits / total if total else 0,
        "replacement_characters": text.count("�"),
        "details": details,
    }


def extract_pypdf(path: Path) -> tuple[str, float, dict]:
    started = time.perf_counter()
    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    elapsed = time.perf_counter() - started
    return "\n\n--- PAGE BREAK ---\n\n".join(pages), elapsed, {"pages": len(pages)}


def extract_docling(converter: DocumentConverter, path: Path) -> tuple[str, float, dict, dict]:
    started = time.perf_counter()
    result = converter.convert(path)
    elapsed = time.perf_counter() - started
    markdown = result.document.export_to_markdown()
    document_json = result.document.export_to_dict()
    page_count = len(document_json.get("pages", {}))
    return markdown, elapsed, {"pages": page_count}, document_json


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    converter = DocumentConverter()
    report = {"documents": {}}
    for university, path in PDFS.items():
        if not path.exists():
            raise FileNotFoundError(path)
        pypdf_text, pypdf_seconds, pypdf_meta = extract_pypdf(path)
        docling_text, docling_seconds, docling_meta, docling_json = extract_docling(converter, path)
        (OUTPUT / f"{university}-pypdf.txt").write_text(pypdf_text, encoding="utf-8")
        (OUTPUT / f"{university}-docling.md").write_text(docling_text, encoding="utf-8")
        (OUTPUT / f"{university}-docling.json").write_text(
            json.dumps(docling_json, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        report["documents"][university] = {
            "source": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "pypdf": {
                "seconds": round(pypdf_seconds, 3),
                "characters": len(pypdf_text),
                **pypdf_meta,
                **score(pypdf_text, university),
            },
            "docling": {
                "seconds": round(docling_seconds, 3),
                "characters": len(docling_text),
                **docling_meta,
                **score(docling_text, university),
            },
        }
    (OUTPUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
