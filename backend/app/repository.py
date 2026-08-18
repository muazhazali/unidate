import json
from datetime import date
from pathlib import Path

from .models import CalendarEvent, Source, University


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _read_json(name: str) -> list[dict]:
    with (DATA_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def universities() -> list[University]:
    return [University.model_validate(item) for item in _read_json("universities.json")]


def events() -> list[CalendarEvent]:
    return [CalendarEvent.model_validate(item) for item in _read_json("events.json")]


def sources() -> list[Source]:
    return [Source.model_validate(item) for item in _read_json("sources.json")]


def filter_events(
    *,
    university_codes: set[str] | None = None,
    academic_session: str | None = None,
    semester: str | None = None,
    event_type: str | None = None,
    query: str | None = None,
    starts_on_or_after: date | None = None,
    ends_on_or_before: date | None = None,
) -> list[CalendarEvent]:
    result = events()
    if university_codes:
        result = [event for event in result if event.university_code in university_codes]
    if academic_session:
        result = [event for event in result if event.academic_session == academic_session]
    if semester:
        needle = semester.casefold()
        result = [event for event in result if event.semester and event.semester.casefold() == needle]
    if event_type:
        result = [event for event in result if event.event_type.value == event_type]
    if query:
        needle = query.casefold()
        result = [
            event
            for event in result
            if needle in event.title.casefold()
            or (event.audience and needle in event.audience.casefold())
        ]
    if starts_on_or_after:
        result = [
            event
            for event in result
            if (event.end_date or event.start_date) >= starts_on_or_after
        ]
    if ends_on_or_before:
        result = [event for event in result if event.start_date <= ends_on_or_before]
    return sorted(result, key=lambda event: (event.start_date, event.university_code, event.title))

