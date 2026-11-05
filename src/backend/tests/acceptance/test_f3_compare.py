"""F3 — Culture Comparison (US11)."""
import pytest

from tests.conftest import ac, assert_problem, route

pytestmark = [pytest.mark.db, route("POST", "/api/ai/compare")]


def compare(client, a, b, topic, lang="vi"):
    return client.post("/api/ai/compare", json={"countryA": a, "countryB": b, "topic": topic, "lang": lang})


def cells(result):
    for s in result["similarities"]:
        yield s
    for row in result["rows"]:
        yield row["a"]
        yield row["b"]


@ac("AC11.1")
def test_reviewed_comparison_served_from_cache(client, fake_llm):
    r = compare(client, "VN", "JP", "gift_giving")
    assert r.status_code == 200
    c = r.json()
    assert c["reviewed"] is True and c["reviewedBy"]
    assert c["similarities"] and c["rows"]
    assert fake_llm.calls == [], "bản đã duyệt không được gọi LLM"


@ac("AC11.2")
def test_missing_evidence_cell_is_null_never_filled(client):
    c = compare(client, "VN", "JP", "gift_giving").json()
    assert any(cell is None for cell in cells(c)), "ô thiếu nguồn phải là null"
    source_ids = {s["id"] for s in c["sources"]}
    for cell in cells(c):
        if cell is not None:
            assert cell["sourceIds"] and set(cell["sourceIds"]) <= source_ids


@ac("AC11.3", "AC11.2")
def test_uncached_comparison_is_generated_as_draft(client, db):
    r = compare(client, "VN", "FR", "food_dining")
    assert r.status_code == 200
    c = r.json()
    assert c["reviewed"] is False
    row = db.execute("""SELECT status, origin FROM comparisons cp
                        JOIN countries a ON a.id = cp.country_a_id JOIN countries b ON b.id = cp.country_b_id
                        WHERE a.iso2 = 'VN' AND b.iso2 = 'FR' AND topic = 'food_dining'""").fetchone()
    assert row == ("draft", "ai_generated")
    # FakeLLM trả một ô không có bằng chứng → API phải trả null, không để LLM tự lấp
    assert c["rows"][0]["b"] is None
    for cell in cells(c):
        assert cell is None or cell["sourceIds"]


@ac("AC11.4")
def test_same_country_rejected(client):
    assert_problem(compare(client, "VN", "VN", "gift_giving"), 400)


@ac("AC11.4")
def test_unknown_topic_rejected(client):
    assert_problem(compare(client, "VN", "JP", "weather"), 400)
