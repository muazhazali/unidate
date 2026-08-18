from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthcheck():
    assert client.get("/healthz").json() == {"status": "ok"}


def test_filter_events_by_university():
    response = client.get("/api/v1/events", params={"universities": "um"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] > 0
    assert all(item["university_code"] == "um" for item in payload["items"])


def test_date_overlap_filter_keeps_spanning_events():
    response = client.get(
        "/api/v1/events",
        params={"universities": "um", "start": "2027-01-01", "end": "2027-01-02"},
    )
    assert response.status_code == 200
    assert any(item["title"] == "Lectures" for item in response.json()["items"])


def test_ics_is_valid_calendar():
    response = client.get("/api/v1/calendar.ics", params={"universities": "um,ukm"})
    assert response.status_code == 200
    assert response.text.startswith("BEGIN:VCALENDAR\r\n")
    assert response.text.endswith("END:VCALENDAR\r\n")
    assert "BEGIN:VEVENT" in response.text


def test_unknown_university_returns_404():
    assert client.get("/api/v1/universities/nope").status_code == 404

