import json
from datetime import UTC, datetime
import httpx
import pytest
from pydantic import ValidationError
from app.extraction_models import NormalizedEventBatch
from app.ollama_cloud import OllamaCloudClient
from scripts.sync_calendars import DATA, build_proposal, discover_document, discover_uitm_sections, extract_html, read_json

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

def test_html_primary_source_does_not_fetch_reference_pdf():
    source = {
        **SOURCE,
        "url": "https://example.test/calendar",
        "document_url": "https://example.test/calendar.pdf",
        "format": "html",
        "parser": "html",
    }
    response = httpx.Response(
        200,
        content=b"<main>Web calendar</main>",
        headers={"content-type": "text/html"},
        request=httpx.Request("GET", source["url"]),
    )

    class NoPdfClient:
        def get(self, _):
            raise AssertionError("reference PDF must not be fetched")

    final_url, content, content_type = discover_document(source, response, NoPdfClient())
    assert final_url == source["url"]
    assert content == b"<main>Web calendar</main>"
    assert content_type == "text/html"

def test_html_scopes_uitm_page_to_exact_calendar_panel():
    html = b'''<main>
      <div class="sppb-panel"><span class="sppb-panel-title">GROUP A: SEMESTER MARCH 20272</span><p>Group A event</p></div>
      <div class="sppb-panel"><span class="sppb-panel-title">GROUP B: SEMESTER MARCH 20262</span><p>Old Group B event</p></div>
      <div class="sppb-panel"><span class="sppb-panel-title">GROUP B: SEMESTER MARCH 20272</span><p>Target Group B event</p><a href="calendar.pdf">PDF</a></div>
    </main>'''
    document = extract_html(html, "https://example.test/calendars", section_match=["GROUP B:", "MARCH", "20272"])
    text = json.dumps(document)
    assert "Target Group B event" in text
    assert "Group A event" not in text
    assert "Old Group B event" not in text
    assert "https://example.test/calendar.pdf" in text

def test_html_fails_closed_when_uitm_section_is_missing():
    html = b'<main><div class="sppb-panel"><span class="sppb-panel-title">GROUP A</span></div></main>'
    with pytest.raises(ValueError, match="calendar section not found"):
        extract_html(html, "https://example.test", section_match=["GROUP B", "20272"])

def test_uitm_uses_one_automatic_catalog_source():
    sources = [source for source in read_json(DATA / "sources.json", [])
               if source["university_code"] == "uitm"]
    assert len(sources) == 1
    assert sources[0]["parser"] == "uitm_sections"
    assert sources[0]["minimum_academic_session"] == "2026/2027"

def test_uitm_discovers_new_semester_automatically():
    html = b'''<main>
      <div class="sppb-panel"><span class="sppb-panel-title">SUMMARY SCHEDULE FOR SESSION 2026/2027: GROUP B</span><a href="summary.pdf">PDF</a></div>
      <div class="sppb-panel"><span class="sppb-panel-title">GROUP B: PROGRAMMES SEMESTER MARCH - JULY 2027 (20272)</span><a href="old.pdf">PDF</a></div>
      <div class="sppb-panel"><span class="sppb-panel-title">GROUP B: PROGRAMMES SEMESTER SEPTEMBER 2027 - FEBRUARY 2028 (20274)</span><a href="new.pdf">PDF</a></div>
    </main>'''
    catalog = {"minimum_academic_session": "2026/2027", "last_checked": "2026-08-19"}
    sources = discover_uitm_sections(html, "https://example.test/calendars", catalog)
    by_id = {source["id"]: source for source in sources}
    assert set(by_id) == {"uitm-group-b-summary-2026", "uitm-group-b-20272", "uitm-group-b-20274"}
    assert by_id["uitm-group-b-20274"]["academic_session"] == "2027/2028"
    assert by_id["uitm-group-b-20274"]["document_url"] == "https://example.test/new.pdf"
    assert by_id["uitm-group-b-20274"]["parser"] == "html"
