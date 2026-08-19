"""Validated boundary between untrusted LLM output and UniDate proposals."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import EventType


class NormalizedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    semester: str | None = Field(default=None, max_length=100)
    audience: str | None = Field(default=None, max_length=300)
    event_type: EventType
    start_date: date
    end_date: date | None = None
    source_page: int | None = Field(default=None, ge=1)
    evidence: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def dates_are_ordered(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class NormalizedEventBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[NormalizedEvent]

