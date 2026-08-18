from scripts.sync_calendars import extract_candidates


def test_extracts_english_cross_month_range():
    pages = [{"page": 2, "text": "Lectures\n28 September – 20 December 2026\n12 Weeks"}]
    candidates = extract_candidates(pages, "2026/2027")
    assert candidates[0]["start_date"] == "2026-09-28"
    assert candidates[0]["end_date"] == "2026-12-20"
    assert candidates[0]["source_page"] == 2


def test_extracts_malay_same_month_range():
    pages = [{"page": 1, "text": "Minggu Ulangkaji\n11 - 17 Januari 2027"}]
    candidates = extract_candidates(pages, "2026/2027")
    assert candidates[0]["start_date"] == "2027-01-11"
    assert candidates[0]["end_date"] == "2027-01-17"
