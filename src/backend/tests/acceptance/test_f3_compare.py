"""F3 — Culture Comparison (US11)."""
import pytest

from tests.conftest import ac, assert_problem, route

pytestmark = [pytest.mark.db, route("POST", "/api/ai/compare")]


def compare(client, a, b, topic, lang="vi"):
    return client.post("/api/ai/compare", json={"countryA": a, "countryB": b, "topic": topic, "lang": lang})


def cells(result):
    yield from result["similarities"]
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


@ac("AC11.1")
def test_reversed_pair_served_from_cache_with_swapped_columns(client, fake_llm):
    c = compare(client, "JP", "VN", "gift_giving").json()
    assert c["reviewed"] is True and (c["countryA"], c["countryB"]) == ("JP", "VN")
    assert c["rows"][0]["a"]["text"] == "Trao và nhận bằng hai tay." and c["rows"][1]["b"] is None
    assert fake_llm.calls == []


@ac("AC11.3")
def test_generated_draft_is_reused_without_new_llm_call(client, fake_llm):
    first = compare(client, "VN", "FR", "food_dining").json()
    calls = len(fake_llm.calls)
    again = compare(client, "VN", "FR", "food_dining").json()
    assert len(fake_llm.calls) == calls, "bản nháp đã lưu phải được dùng lại"
    assert again["reviewed"] is False and again["rows"] == first["rows"]


@ac("AC11.2")
def test_no_evidence_at_all_means_no_llm_call_and_no_draft(client, fake_llm, db):
    c = compare(client, "KE", "FR", "taboos").json()
    assert c["rows"] == [] and c["similarities"] == [] and c["insufficient"]
    assert fake_llm.calls == []
    assert db.execute("SELECT count(*) FROM comparisons WHERE topic = 'taboos'").fetchone() == (0,)


@ac("AC11.3")
def test_llm_outage_returns_503_and_stores_nothing(client, fake_llm, db):
    fake_llm.fail = True
    assert_problem(compare(client, "VN", "FR", "food_dining"), 503)
    assert db.execute("SELECT count(*) FROM comparisons WHERE topic = 'food_dining'").fetchone() == (0,)


@ac("AC11.4")
def test_unknown_country_is_404(client):
    assert_problem(compare(client, "VN", "ZZ", "gift_giving"), 404)


@ac("AC11.2")
def test_cells_only_accept_evidence_of_their_own_country():
    """LLM lấy bằng chứng của nước B điền vào ô nước A, hoặc nêu điểm giống chỉ dựa trên một nước → null / bỏ."""
    from app.ai.retrieval import Evidence
    from app.services.comparison_service import _Country, validate
    vn, jp = _Country(1, "VN", "Việt Nam", "Vietnam"), _Country(3, "JP", "Nhật Bản", "Japan")
    ev = [Evidence("c1", 1, "claim", "VN text", "VN", 4, "t", "p", "u", "l", 1.0),
          Evidence("c2", 2, "claim", "JP text", "JP", 1, "t", "p", "u", "l", 1.0)]
    raw = {"similarities": [{"text": "Chỉ dựa trên VN", "evidence": ["c1"]}, {"text": "Cả hai [c1][c2]", "evidence": ["c1", "c2"]}],
           "rows": [{"aspect": "Trao quà", "a": {"text": "Dùng bằng chứng JP", "evidence": ["c2"]},
                     "b": {"text": "Hai tay [c2]", "evidence": ["c2", "c2"]}},
                    {"aspect": "Gói quà", "a": {"text": "Nhãn bịa", "evidence": ["c9"]}, "b": {"text": "", "evidence": []}}],
           "context": "", "caveats": [], "insufficient": []}
    out = validate(raw, vn, jp, ev, "vi")
    assert out["similarities"] == [{"text": "Cả hai", "sourceIds": [4, 1]}]
    assert out["rows"][0] == {"aspect": "Trao quà", "a": None, "b": {"text": "Hai tay", "sourceIds": [1]}}
    assert out["rows"][1]["a"] is None and out["rows"][1]["b"] is None
    assert out["insufficient"] == ["Trao quà (Việt Nam)", "Gói quà (Việt Nam)", "Gói quà (Nhật Bản)"]
