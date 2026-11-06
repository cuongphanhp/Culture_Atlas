"""F2 — Câu hỏi gợi ý của AI Guide theo quốc gia và mối quan tâm (AC10.3, AC10.4). LLM là FakeLLM."""
import pytest

from app.ai.suggestions import detect_interests, load_bank, suggest
from tests.conftest import JSON_HEADERS, ac, route

GIFT_Q = "Ở Nhật Bản tặng quà cần lưu ý gì?"
OLD_TEMPLATES = ("cần biết những phép lịch sự nào?", "Tặng quà ở {} cần lưu ý gì?", "có những lễ hội truyền thống nào?")


def _ask(client, message, **body):
    r = client.post("/api/ai/chat", json={"message": message, **body}, headers=JSON_HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


def _bank_country(text: str) -> str | None:
    """Quốc gia của câu gợi ý theo ngân hàng câu hỏi (None nếu không thuộc nước nào)."""
    for iso, cats in load_bank()["countries"].items():
        if any(text in qs for qs in cats.values()):
            return iso
    return None


# ── Không cần DB: suy ra mối quan tâm, chọn câu ──
@ac("AC10.4")
@pytest.mark.parametrize(("questions", "expected"), [
    (["Ở Nhật Bản tặng quà cần lưu ý gì?"], "gift_giving"),
    (["tang qua o nhat ban can luu y gi"], "gift_giving"),               # gõ không dấu
    (["Người Việt ăn gì ngày Tết?"], "food_dining"),
    (["Ăn mặc khi đến Ai Cập thế nào?"], "clothing"),                     # "ăn mặc" không phải ẩm thực
    (["Hát quan họ là gì?", "Múa rối nước có từ bao giờ?"], "arts_music"),
])
def test_interest_detected_from_questions(questions, expected):
    assert detect_interests(questions)[0] == expected


@ac("AC10.4")
def test_recent_question_weighs_more_and_ambiguous_words_ignored():
    assert detect_interests(["Tặng quà ở Nhật thế nào?", "Ẩm thực Nhật có gì đặc biệt?"])[0] == "food_dining"
    assert detect_interests(["Hay quá, cảm ơn"]) == [], "“quá” không phải “quà”"
    assert detect_interests(["Thủ đô là gì?"]) == []


@ac("AC10.3")
def test_every_country_has_specific_questions_not_name_swapped_templates():
    bank = load_bank()["countries"]
    assert set(bank) == {"VN", "JP", "KR", "CN", "TH", "IN", "FR", "MX", "EG", "KE"}
    seen: set[str] = set()
    for iso, cats in bank.items():
        assert len(cats) >= 6, f"{iso}: cần đủ chủ đề để gợi ý theo mối quan tâm"
        for qs in cats.values():
            for q in qs:
                assert q not in seen, f"câu gợi ý trùng giữa các nước: {q}"
                seen.add(q)


@ac("AC10.4")
def test_top_interest_gets_two_then_explores_another_topic():
    got = suggest("JP", [GIFT_Q], n=3)
    assert [s.category for s in got][:2] == ["gift_giving", "gift_giving"]
    assert got[2].category != "gift_giving" and all(s.country == "JP" for s in got)
    assert GIFT_Q not in [s.text for s in got]


@ac("AC10.3")
def test_topics_with_data_come_first():
    got = suggest("KE", [], n=3, available={"heritage"})
    assert got[0].category == "heritage"


# ── API ──
@route("GET", "/api/ai/suggestions")
@ac("AC10.3")
@pytest.mark.db
def test_suggestions_follow_context_country(client, fake_llm):
    jp = client.get("/api/ai/suggestions", params={"country": "jp"}).json()
    kr = client.get("/api/ai/suggestions", params={"country": "KR"}).json()
    assert jp["country"] == "JP" and kr["country"] == "KR"
    assert len(jp["questions"]) == 4 and all(q["country"] == "JP" for q in jp["questions"])
    assert all(_bank_country(q["text"]) == "JP" for q in jp["questions"])
    assert {q["text"] for q in jp["questions"]}.isdisjoint({q["text"] for q in kr["questions"]})
    assert fake_llm.calls == [], "gợi ý không gọi LLM"


@route("GET", "/api/ai/suggestions")
@ac("AC10.3")
@pytest.mark.db
def test_suggestions_do_not_consume_quota_and_validate_params(client):
    for _ in range(12):
        assert client.get("/api/ai/suggestions").status_code == 200
    assert client.get("/api/ai/suggestions", params={"country": "Japan"}).status_code == 400
    assert client.get("/api/ai/suggestions", params={"category": "khong-co"}).status_code == 400
    general = client.get("/api/ai/suggestions", params={"limit": 3}).json()
    assert general["country"] is None and len(general["questions"]) == 3


@route("GET", "/api/ai/suggestions")
@ac("AC10.4")
@pytest.mark.db
def test_suggestions_follow_session_interest_and_country(client):
    sid = _ask(client, GIFT_Q)["sessionId"]
    r = client.get("/api/ai/suggestions", params={"sessionId": sid}).json()     # không truyền country → nước của phiên
    assert r["country"] == "JP" and r["interests"][0] == "gift_giving"
    cats = [q["category"] for q in r["questions"]]
    assert cats[:2] == ["gift_giving", "gift_giving"] and len(set(cats)) >= 2
    assert GIFT_Q not in [q["text"] for q in r["questions"]]


@route("GET", "/api/ai/suggestions")
@ac("AC10.4")
@pytest.mark.db
def test_page_category_is_top_interest(client):
    r = client.get("/api/ai/suggestions", params={"country": "VN", "category": "food_dining"}).json()
    assert r["interests"][0] == "food_dining" and r["questions"][0]["category"] == "food_dining"


@route("GET", "/api/ai/suggestions")
@ac("AC10.4")
@pytest.mark.db
def test_other_clients_session_not_used_for_suggestions(client):
    sid = _ask(client, GIFT_Q)["sessionId"]
    r = client.get("/api/ai/suggestions", params={"sessionId": sid}, headers={"X-Client-Id": "khach-khac-0001"}).json()
    assert r["interests"] == [] and r["country"] is None


@route("POST", "/api/ai/chat")
@ac("AC10.3")
@pytest.mark.db
def test_chat_follow_ups_follow_context_country_without_rag(client):
    a = _ask(client, "Xin chào", context={"country": "TH"})
    assert a["route"] == "smalltalk" and len(a["followUpQuestions"]) == 3
    assert all(_bank_country(q) == "TH" for q in a["followUpQuestions"])
    for q in a["followUpQuestions"]:
        assert not any(t.format("Thái Lan") in q or q.endswith(t) for t in OLD_TEMPLATES), q


@route("POST", "/api/ai/chat")
@ac("AC10.3", "AC10.4")
@pytest.mark.db
def test_llm_follow_ups_get_country_interest_and_grounded_examples(client, fake_llm):
    a = _ask(client, GIFT_Q)
    prompt = next(c for c in fake_llm.calls if c.get("name") == "follow_ups")["messages"]
    assert "Nhật Bản" in prompt[0]["content"] and "tặng quà" in prompt[0]["content"]
    assert "Omiyage ở Nhật Bản là gì?" in prompt[1]["content"], "LLM nhận câu gợi ý mẫu có nguồn của đúng nước"
    assert len(a["followUpQuestions"]) == 3 and GIFT_Q not in a["followUpQuestions"]


@route("POST", "/api/ai/chat")
@ac("AC10.3")
@pytest.mark.db
def test_follow_ups_fall_back_to_country_bank_when_llm_json_fails(client, fake_llm):
    fake_llm.json.pop("follow_ups")
    a = _ask(client, GIFT_Q)
    assert len(a["followUpQuestions"]) == 3 and all(_bank_country(q) == "JP" for q in a["followUpQuestions"])
