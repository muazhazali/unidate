from datetime import date, timedelta
from hashlib import sha256

from .models import CalendarEvent, University


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _date(value: date) -> str:
    return value.strftime("%Y%m%d")


def build_calendar(events: list[CalendarEvent], universities: dict[str, University]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//UniDate//Academic Calendars//MS",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:UniDate",
    ]
    for event in events:
        university = universities[event.university_code]
        uid_hash = sha256(f"{event.id}:{event.start_date}".encode()).hexdigest()[:24]
        end_exclusive = (event.end_date or event.start_date) + timedelta(days=1)
        description = f"{university.name} | Sumber/Source: {event.source_url}"
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid_hash}@unidate",
                f"DTSTART;VALUE=DATE:{_date(event.start_date)}",
                f"DTEND;VALUE=DATE:{_date(end_exclusive)}",
                f"SUMMARY:{_escape(f'[{university.short_name}] {event.title}')}",
                f"DESCRIPTION:{_escape(description)}",
                f"URL:{event.source_url}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"

