import json
from datetime import UTC, datetime
import httpx
import pytest
from pydantic import ValidationError
from app.extraction_models import NormalizedEventBatch
from app.ollama_cloud import OllamaCloudClient
from scripts.sync_calendars import build_proposal, extract_html

SOURCE = {"id": "uum-undergraduate-2026", "university_code": "uum", "academic_session": "2026/2027", "audience": "Undergraduate students", "title": "Calendar"}

def valid_batch():
    return NormalizedEventBatch.model_validate({"events": [{"title": "MINGGU SUAIKENAL", "semester": "Semester Pertama",
        "audience": "Undergraduate students", "event_type": "orientation", "start_date": "2026-09-20",
        "end_date": "2026-09-26", "source_page": None,
        "evidence": "MINGGU SUAIKENAL 20 - 26 September 2026", "confidence": 0.98}]})

def test_pydantic_rejects_backwards_dates():
    data = valid_batch().model_dump(mode="json"); data["events"][0]["end_date"] = "2026-09-01"
    with pytest.raises(ValidationError): NormalizedEventBatch.model_validate(data)

def test_ollama_retries_invalid_json_then_validates():
    calls = 0
    def handler(request):
        nonlocal calls; calls += 1
        content = "not json" if calls == 1 else json.dumps(valid_batch().model_dump(mode="json"))
        return httpx.Response(200, json={"message": {"content": content}})
    client = OllamaCloudClient(api_key="test", model="test-model", transport=httpx.MockTransport(handler), sleep=lambda _: None)
    assert client.normalize(document={"extractor": "test"}, source=SOURCE).events[0].title == "MINGGU SUAIKENAL"
    assert calls == 2

def test_html_to_complete_proposal_end_to_end():
    class FakeNormalizer:
        def normalize(self, **_): return valid_batch()
    document = extract_html(b"<main><h2>Semester Pertama</h2><p>MINGGU SUAIKENAL 20 - 26 September 2026</p></main>", "https://example.test", "2026/2027")
    proposal = build_proposal(SOURCE, final_url="https://example.test", digest="abc", previous=None,
        detected_at=datetime(2026, 8, 19, tzinfo=UTC), document=document, normalizer=FakeNormalizer())
    event = proposal["candidate_events"][0]
    assert proposal["schema_version"] == 2
    assert event["university_code"] == "uum" and event["source_url"] == "https://example.test"
    assert event["review_status"] == "needs_review"

def test_html_scopes_uum_page_to_requested_session():
    html = b'''<div class="sppb-panel sppb-panel-custom"><span aria-label="2026/2027 SESSION"></span><table><tr><td>Current event</td></tr></table></div>
    <div class="sppb-panel sppb-panel-custom"><span aria-label="2025/2026 SESSION"></span><table><tr><td>Old event</td></tr></table></div>'''
    document = extract_html(html, "https://example.test", "2026/2027")
    text = json.dumps(document)
    assert "Current event" in text and "Old event" not in text
