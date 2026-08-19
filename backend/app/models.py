from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, model_validator


class EventType(StrEnum):
    registration = "registration"
    orientation = "orientation"
    lecture = "lecture"
    assessment = "assessment"
    mid_semester_break = "mid_semester_break"
    revision = "revision"
    examination = "examination"
    semester_break = "semester_break"
    public_holiday = "public_holiday"
    convocation = "convocation"
    other = "other"


class University(BaseModel):
    code: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    short_name: str
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    website: HttpUrl


class CalendarEvent(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    university_code: str
    academic_session: str = Field(pattern=r"^\d{4}/\d{4}$")
    semester: str | None = None
    audience: str | None = None
    event_type: EventType
    title: str
    start_date: date
    end_date: date | None = None
    source_url: HttpUrl
    source_page: int | None = Field(default=None, ge=1)
    last_checked: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class Source(BaseModel):
    id: str
    university_code: str
    academic_session: str
    title: str
    url: HttpUrl
    document_url: HttpUrl | None = None
    section_match: list[str] | None = None
    minimum_academic_session: str | None = None
    format: str
    parser: str
    audience: str | None = None
    last_checked: date | None = None
    content_hash: str | None = None


class EventPage(BaseModel):
    items: list[CalendarEvent]
    total: int
    page: int
    page_size: int
    has_next: bool
