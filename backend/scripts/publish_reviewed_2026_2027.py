"""Publish the human-reviewed 2026/2027 proposal batch.

UniMAP calendar tables contain vertically merged cells that the automated
normalizer cannot reliably associate with date rows. Their academic periods are
therefore transcribed below from the rendered official PDFs. Other sources use
their validated proposal candidates with small, documented OCR cleanup.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from pydantic import TypeAdapter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "data"
TODAY = date(2026, 8, 19)
SESSION = "2026/2027"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def proposal(source_id: str) -> dict:
    return read_json(DATA / "proposals" / f"2026-08-19-{source_id}.json")


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return value[:46].rstrip("-") or "event"


def event(*, university: str, title: str, start: str, end: str | None,
          event_type: str, semester: str | None, audience: str | None,
          source_url: str, source_page: int | None = 1) -> dict:
    return {
        "university_code": university,
        "academic_session": SESSION,
        "semester": semester,
        "audience": audience,
        "event_type": event_type,
        "title": title,
        "start_date": start,
        "end_date": end,
        "source_url": source_url,
        "source_page": source_page,
        "last_checked": TODAY.isoformat(),
    }


def proposal_events(source_id: str) -> list[dict]:
    batch = proposal(source_id)
    result = []
    for candidate in batch["candidate_events"]:
        title = candidate["title"]
        if source_id == "uitm-main-2026":
            title = re.sub(r"^o\s+", "", title)
        result.append(event(
            university=batch["university_code"], title=title,
            start=candidate["start_date"], end=candidate.get("end_date"),
            event_type=candidate["event_type"], semester=candidate.get("semester"),
            audience=candidate.get("audience") or (
                "Pre-Diploma, Diploma, Bachelor, Master and Doctoral"
                if source_id == "uitm-main-2026" else None
            ), source_url=batch["source_url"], source_page=candidate.get("source_page"),
        ))
    return result


def unimap_events() -> list[dict]:
    diploma = proposal("unimap-calendar-2026")
    bachelor = proposal("unimap-bachelor-2026")
    d_url, b_url = diploma["source_url"], bachelor["source_url"]
    rows: list[dict] = []

    def add(program: str, source_url: str, semester: str, title: str,
            start: str, end: str | None, kind: str):
        rows.append(event(university="unimap", title=title, start=start, end=end,
                          event_type=kind, semester=semester, audience=program,
                          source_url=source_url))

    # Diploma programme: visually reviewed against the official one-page table.
    add("Diploma", d_url, "Semester 1", "Pendaftaran Pelajar Baharu / Registration for New Students", "2026-06-13", None, "registration")
    add("Diploma", d_url, "Semester 1", "Minggu Suai Kenal/Orientation week", "2026-06-15", "2026-06-21", "orientation")
    add("Diploma", d_url, "Semester 1", "KULIAH/LECTURES (7 MINGGU/WEEKS)", "2026-06-22", "2026-08-09", "lecture")
    add("Diploma", d_url, "Semester 1", "CUTI PERT. SEMESTER / MID. SEMESTER BREAK (1 MINGGU/WEEK)", "2026-08-10", "2026-08-16", "mid_semester_break")
    add("Diploma", d_url, "Semester 1", "KULIAH/LECTURES (7 MINGGU/WEEKS)", "2026-08-17", "2026-10-04", "lecture")
    add("Diploma", d_url, "Semester 1", "MINGGU ULANG KAJI / REVISION WEEK (1 MINGGU/WEEK)", "2026-10-05", "2026-10-11", "revision")
    add("Diploma", d_url, "Semester 1", "PEPERIKSAAN AKHIR / FINAL EXAMINATION (2 MINGGU/WEEKS)", "2026-10-12", "2026-10-25", "examination")
    add("Diploma", d_url, "Semester 1", "CUTI ANTARA SEMESTER/ SEMESTER BREAK (3 MINGGU/WEEKS)", "2026-10-26", "2026-11-15", "semester_break")
    add("Diploma", d_url, "Semester 2", "KULIAH/LECTURES (5 MINGGU/WEEKS)", "2026-11-16", "2026-12-20", "lecture")
    add("Diploma", d_url, "Semester 2", "CUTI PERT. SEMESTER / MID. SEM. BREAK (1 MINGGU/WEEK)", "2026-12-21", "2026-12-27", "mid_semester_break")
    add("Diploma", d_url, "Semester 2", "KULIAH/LECTURES (9 MINGGU/WEEKS)", "2026-12-28", "2027-02-28", "lecture")
    add("Diploma", d_url, "Semester 2", "MINGGU ULANG KAJI / REVISION WEEK (2 MINGGU/WEEKS)", "2027-03-01", "2027-03-14", "revision")
    add("Diploma", d_url, "Semester 2", "PEPERIKSAAN AKHIR / FINAL EXAMINATION (2 MINGGU/WEEKS)", "2027-03-15", "2027-03-28", "examination")
    add("Diploma", d_url, "Additional Semester", "KULIAH/LECTURES (4 MINGGU/WEEKS)", "2027-03-29", "2027-04-25", "lecture")
    add("Diploma", d_url, "Additional Semester", "PEPERIKSAAN/ EXAMINATION (1 MINGGU/WEEK)", "2027-04-26", "2027-05-02", "examination")
    add("Diploma", d_url, "Additional Semester", "CUTI ANTARA SIDANG / SEMESTER BREAK (5 MINGGU/WEEKS)", "2027-05-03", "2027-06-06", "semester_break")
    add("Diploma", d_url, "Short Semester", "KULIAH/LECTURES (7 MINGGU/WEEKS)", "2027-03-29", "2027-05-16", "lecture")
    add("Diploma", d_url, "Short Semester", "MINGGU ULANG KAJI / REVISION WEEK (1 MINGGU/WEEK)", "2027-05-17", "2027-05-23", "revision")
    add("Diploma", d_url, "Short Semester", "PEPERIKSAAN / EXAMINATION (1 MINGGU/WEEK)", "2027-05-24", "2027-05-30", "examination")
    add("Diploma", d_url, "Short Semester", "CUTI ANTARA SIDANG / SEMESTER BREAK (1 MINGGU/WEEK)", "2027-05-31", "2027-06-06", "semester_break")

    # Bachelor programme: visually reviewed against its separate official table.
    add("Bachelor Degree", b_url, "Semester 1", "Pendaftaran Pelajar Baharu / Registration for New Students", "2026-09-26", None, "registration")
    add("Bachelor Degree", b_url, "Semester 1", "Minggu Suai Kenal/Orientation week", "2026-09-28", "2026-10-04", "orientation")
    add("Bachelor Degree", b_url, "Semester 1", "KULIAH/LECTURES (8 MINGGU/WEEKS)", "2026-10-05", "2026-11-29", "lecture")
    add("Bachelor Degree", b_url, "Semester 1", "CUTI PERT. SEMESTER / MID. SEMESTER BREAK (1 MINGGU/WEEK)", "2026-11-30", "2026-12-06", "mid_semester_break")
    add("Bachelor Degree", b_url, "Semester 1", "KULIAH/LECTURES (6 MINGGU/WEEKS)", "2026-12-07", "2027-01-17", "lecture")
    add("Bachelor Degree", b_url, "Semester 1", "MINGGU ULANG KAJI / REVISION WEEK (1 MINGGU/WEEK)", "2027-01-18", "2027-01-24", "revision")
    add("Bachelor Degree", b_url, "Semester 1", "PEPERIKSAAN AKHIR/ FINAL EXAMINATION (2 MINGGU/WEEKS)", "2027-01-25", "2027-02-07", "examination")
    add("Bachelor Degree", b_url, "Semester 1", "CUTI ANTARA SEMESTER / SEMESTER BREAK (4 MINGGU/WEEKS)", "2027-02-08", "2027-03-07", "semester_break")
    add("Bachelor Degree", b_url, "Semester 2", "KULIAH/LECTURES (10 MINGGU/WEEKS)", "2027-03-08", "2027-05-16", "lecture")
    add("Bachelor Degree", b_url, "Semester 2", "CUTI PERT. SEMESTER / MID. SEMESTER BREAK (1 MINGGU/WEEK)", "2027-05-17", "2027-05-23", "mid_semester_break")
    add("Bachelor Degree", b_url, "Semester 2", "KULIAH/LECTURES (4 MINGGU/WEEKS)", "2027-05-24", "2027-06-20", "lecture")
    add("Bachelor Degree", b_url, "Semester 2", "MINGGU ULANG KAJI / REVISION WEEKS (1 MINGGU/WEEK)", "2027-06-21", "2027-06-27", "revision")
    add("Bachelor Degree", b_url, "Semester 2", "PEPERIKSAAN AKHIR/ FINAL EXAMINATION (2 MINGGU/WEEKS)", "2027-06-28", "2027-07-11", "examination")
    add("Bachelor Degree", b_url, "Additional Semester", "TUTORIAL (4 MINGGU/WEEKS)", "2027-07-12", "2027-08-08", "lecture")
    add("Bachelor Degree", b_url, "Additional Semester", "PEPERIKSAAN/ EXAMINATION (1 MINGGU/WEEK)", "2027-08-09", "2027-08-15", "examination")
    add("Bachelor Degree", b_url, "Additional Semester", "CUTI ANTARA SIDANG / SEMESTER BREAK (6 MINGGU/WEEKS)", "2027-08-16", "2027-09-26", "semester_break")
    add("Bachelor Degree", b_url, "Short Semester", "KULIAH/LECTURES (7 MINGGU/WEEKS)", "2027-07-12", "2027-08-29", "lecture")
    add("Bachelor Degree", b_url, "Short Semester", "MINGGU ULANG KAJI / REVISION WEEK (1 MINGGU/WEEK)", "2027-08-30", "2027-09-05", "revision")
    add("Bachelor Degree", b_url, "Short Semester", "PEPERIKSAAN / EXAMINATION (1 MINGGU/WEEK)", "2027-09-06", "2027-09-12", "examination")
    add("Bachelor Degree", b_url, "Short Semester", "CUTI ANTARA SIDANG / SEMESTER BREAK (2 MINGGU/WEEKS)", "2027-09-13", "2027-09-26", "semester_break")

    # Calendar annotations. Merge identical dates appearing in both programmes.
    annotations: dict[tuple, dict] = {}
    for batch in (diploma, bachelor):
        for candidate in batch["candidate_events"]:
            if candidate["event_type"] not in {"public_holiday", "convocation"}:
                continue
            key = (candidate["title"], candidate["start_date"], candidate.get("end_date"), candidate["event_type"])
            item = event(university="unimap", title=candidate["title"], start=candidate["start_date"],
                         end=candidate.get("end_date"), event_type=candidate["event_type"],
                         semester=candidate.get("semester"), audience=("Diploma" if batch is diploma else "Bachelor Degree"),
                         source_url=batch["source_url"], source_page=candidate.get("source_page"))
            if key in annotations:
                annotations[key]["audience"] = "Diploma and Bachelor Degree"
            else:
                annotations[key] = item
    rows.extend(annotations.values())
    return rows


def main() -> None:
    reviewed = []
    for source_id in ("uitm-main-2026", "uum-undergraduate-2026", "um-bachelor-2026", "ukm-main-2026"):
        reviewed.extend(proposal_events(source_id))
    reviewed.extend(unimap_events())
    reviewed_universities = {"uitm", "unimap", "uum", "um", "ukm"}
    existing = read_json(DATA / "events.json")
    retained = [
        item for item in existing
        if item["academic_session"] != SESSION or item["university_code"] not in reviewed_universities
    ]
    events = retained + reviewed
    events.sort(key=lambda item: (item["start_date"], item["university_code"], item["title"], item.get("audience") or ""))
    for index, item in enumerate(events, 1):
        item["id"] = f"{item['university_code']}-{item['start_date']}-{slug(item['title'])}-{index:03d}"
    TypeAdapter(list[__import__("app.models", fromlist=["CalendarEvent"]).CalendarEvent]).validate_python(events)
    (DATA / "events.json").write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts: dict[str, int] = {}
    for item in events:
        counts[item["university_code"]] = counts.get(item["university_code"], 0) + 1
    print(f"retained {len(retained)} out-of-scope events")
    print(f"published {len(reviewed)} reviewed events: {counts}")


if __name__ == "__main__":
    main()
