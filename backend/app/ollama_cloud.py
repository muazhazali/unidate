"""Small Ollama Cloud client with strict validation and correction retries."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Callable

import httpx
from pydantic import ValidationError

from app.extraction_models import NormalizedEventBatch


SYSTEM_PROMPT = """You normalize Malaysian university academic calendars.
Return one JSON object only, matching the supplied JSON schema. Include every dated
calendar event visible in the input. Keep event titles exactly as published; do not
translate, summarize, or invent them. Use ISO dates. If no end date is published,
set end_date to null. Evidence must be a short verbatim excerpt from the input.
Valid event_type values: registration, orientation, lecture, assessment,
mid_semester_break, revision, examination, semester_break, public_holiday,
convocation, other. Never infer an event that is absent from the source."""


def _json_object(text: str) -> dict:
    cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text, flags=re.I)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("response did not contain a JSON object")
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("response JSON must be an object")
    return value


class OllamaCloudClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        max_attempts: int = 3,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.api_key = api_key or os.getenv("OLLAMA_API_KEY")
        self.model = model or os.getenv("OLLAMA_MODEL")
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "https://ollama.com/api")).rstrip("/")
        self.max_attempts = max_attempts
        self.transport = transport
        self.sleep = sleep
        if not self.api_key:
            raise ValueError("OLLAMA_API_KEY is required")
        if not self.model:
            raise ValueError("OLLAMA_MODEL is required")

    def normalize(self, *, document: dict, source: dict) -> NormalizedEventBatch:
        schema = NormalizedEventBatch.model_json_schema()
        prompt = (
            f"University: {source['university_code']}\n"
            f"Academic session: {source['academic_session']}\n"
            f"Default audience: {source.get('audience') or 'not specified'}\n"
            f"JSON schema: {json.dumps(schema, ensure_ascii=False)}\n"
            f"Structured source: {json.dumps(document, ensure_ascii=False)}"
        )
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
        last_error: Exception | None = None
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(base_url=self.base_url, headers=headers, timeout=180, transport=self.transport) as client:
            for attempt in range(1, self.max_attempts + 1):
                try:
                    response = client.post("/chat", json={"model": self.model, "messages": messages, "stream": False})
                    response.raise_for_status()
                    raw = response.json()["message"]["content"]
                    return NormalizedEventBatch.model_validate(_json_object(raw))
                except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as error:
                    last_error = error
                    if attempt == self.max_attempts:
                        break
                    messages.extend([
                        {"role": "assistant", "content": raw if "raw" in locals() else ""},
                        {"role": "user", "content": f"The response failed validation: {error}. Return corrected JSON only."},
                    ])
                    self.sleep(min(2 ** (attempt - 1), 4))
        raise RuntimeError(f"Ollama output failed validation after {self.max_attempts} attempts: {last_error}")

