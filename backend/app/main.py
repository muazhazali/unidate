import os
import time
from collections import defaultdict, deque
from datetime import date

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .ics import build_calendar
from .models import EventPage, EventType
from .repository import events, filter_events, sources, universities


app = FastAPI(
    title="UniDate API",
    version="1.0.0",
    description="Read-only Malaysian university academic calendar API.",
)

origins = [item.strip() for item in os.getenv("UNIDATE_CORS_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

request_windows: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path == "/healthz":
        return await call_next(request)
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = request_windows[client]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= 120:
        return Response(
            content='{"detail":"Rate limit exceeded"}',
            status_code=429,
            media_type="application/json",
            headers={"Retry-After": "60"},
        )
    window.append(now)
    return await call_next(request)


@app.get("/healthz")
def healthcheck():
    return {"status": "ok"}


@app.get("/api/v1/universities")
def list_universities():
    all_events = events()
    counts = {code: 0 for code in [university.code for university in universities()]}
    for event in all_events:
        counts[event.university_code] += 1
    return [university.model_dump(mode="json") | {"event_count": counts[university.code]} for university in universities()]


@app.get("/api/v1/universities/{code}")
def get_university(code: str):
    university = next((item for item in universities() if item.code == code.casefold()), None)
    if not university:
        raise HTTPException(status_code=404, detail="University not found")
    return university


@app.get("/api/v1/sessions")
def list_sessions():
    return ["2026/2027", "2027/2028"]


@app.get("/api/v1/event-types")
def list_event_types():
    return [item.value for item in EventType]


@app.get("/api/v1/sources")
def list_sources(university: str | None = None):
    items = sources()
    if university:
        items = [item for item in items if item.university_code == university.casefold()]
    return items


def _university_set(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {item.strip().casefold() for item in value.split(",") if item.strip()}


@app.get("/api/v1/events", response_model=EventPage)
def list_events(
    universities_filter: str | None = Query(default=None, alias="universities"),
    academic_session: str | None = None,
    semester: str | None = None,
    event_type: str | None = None,
    q: str | None = None,
    start: date | None = None,
    end: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
):
    items = filter_events(
        university_codes=_university_set(universities_filter),
        academic_session=academic_session,
        semester=semester,
        event_type=event_type,
        query=q,
        starts_on_or_after=start,
        ends_on_or_before=end,
    )
    offset = (page - 1) * page_size
    return EventPage(
        items=items[offset : offset + page_size],
        total=len(items),
        page=page,
        page_size=page_size,
        has_next=offset + page_size < len(items),
    )


@app.get("/api/v1/calendar.ics", response_class=PlainTextResponse)
def download_calendar(
    universities_filter: str | None = Query(default=None, alias="universities"),
    academic_session: str | None = None,
    semester: str | None = None,
    event_type: str | None = None,
    q: str | None = None,
    start: date | None = None,
    end: date | None = None,
):
    items = filter_events(
        university_codes=_university_set(universities_filter),
        academic_session=academic_session,
        semester=semester,
        event_type=event_type,
        query=q,
        starts_on_or_after=start,
        ends_on_or_before=end,
    )
    university_map = {university.code: university for university in universities()}
    return PlainTextResponse(
        build_calendar(items, university_map),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="unidate-calendar.ics"'},
    )

