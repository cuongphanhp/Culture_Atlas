"""F2 — AI Cultural Guide (US06–US10). LLM luôn là FakeLLM (tests/fakes.py), không gọi OpenAI."""
import json
import re
import time

import pytest

from tests.conftest import ac, assert_problem, route

pytestmark = [pytest.mark.db, route("POST", "/api/ai/chat")]
JSON = {"Accept": "application/json"}
RAG_Q = "Ở Nhật Bản tặng quà cần lưu ý gì?"
VI_CHARS = set("ăâđêôơưàảãáạằẳẵắặầẩẫấậèẻẽéẹềểễếệìỉĩíịòỏõóọồổỗốộờởỡớợùủũúụừửữứựỳỷỹýỵ")


def ask(client, message, **body):
    r = client.post("/api/ai/chat", json={"message": message, **body}, headers=JSON)
    assert r.status_code == 200, r.text
    return r.json()


def sse_events(resp) -> list[tuple[str, str]]:
    events, name = [], "message"
    for line in resp.iter_lines():
        if line.startswith("event:"):
            name = line[6:].strip()
        elif line.startswith("data:"):
            events.append((name, line[5:].strip()))
    return events


def chunk_country(db) -> dict[int, str]:
    return dict(db.execute("SELECT id, metadata->>'country' FROM entry_chunks").fetchall())


# ── US06 — Hỏi đáp ──
@ac("AC06.2")
def test_simple_fact_answered_from_db_without_llm(client, db, fake_llm):
    a = ask(client, "Thủ đô của Ấn Độ là gì?")
    assert a["route"] == "structured" and "New Delhi" in a["answer"]
    assert fake_llm.calls == []
    assert db.execute("SELECT model FROM chat_logs ORDER BY id DESC LIMIT 1").fetchone()[0] == "structured"


@ac("AC06.1")
def test_streaming_sse_vietnamese_first_token_fast(client):
    t0 = time.perf_counter()
    with client.stream("POST", "/api/ai/chat", json={"message": RAG_Q}, headers={"Accept": "text/event-stream"}) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        ttft = None
        events = []
        for ev in sse_events(r):
            if ttft is None and ev[0] == "token":
                ttft = time.perf_counter() - t0
            events.append(ev)
    names = [e[0] for e in events]
    assert names[0] == "token" and names[-1] == "final"
    assert ttft is not None and ttft < 3.0
    final = json.loads(events[-1][1])
    assert {"messageId", "answer", "citations", "confidence"} <= final.keys()
    assert VI_CHARS & set(final["answer"].lower()), "câu trả lời phải bằng tiếng Việt"


@ac("AC06.3")
def test_guest_rate_limit(client):
    remaining = []
    for _ in range(10):
        r = client.post("/api/ai/chat", json={"message": "Thủ đô của Pháp là gì?"}, headers=JSON)
        assert r.status_code == 200
        remaining.append(int(r.headers["X-RateLimit-Remaining"]))
    assert remaining == sorted(remaining, reverse=True) and remaining[-1] == 0
    body = assert_problem(client.post("/api/ai/chat", json={"message": "Thủ đô của Pháp là gì?"}, headers=JSON), 429)
    assert body.get("detail"), "cần thông báo thân thiện cho người dùng"


@ac("AC06.1")
def test_message_validation(client):
    assert_problem(client.post("/api/ai/chat", json={"message": "a"}, headers=JSON), 400)
    assert_problem(client.post("/api/ai/chat", json={"message": "x" * 1001}, headers=JSON), 400)


@ac("AC06.1")
def test_llm_outage_returns_503(client, fake_llm):
    fake_llm.fail = True
    assert_problem(client.post("/api/ai/chat", json={"message": RAG_Q}, headers=JSON), 503)


# ── US07 — Trích dẫn ──
@ac("AC07.1")
def test_every_citation_marker_resolves(client):
    a = ask(client, RAG_Q)
    assert a["route"] == "rag" and a["confidence"] in {"supported", "inferred"}
    markers = set(re.findall(r"\[(c\d+)\]", a["answer"]))
    ids = {c["id"] for c in a["citations"]}
    assert markers and markers <= ids
    for c in a["citations"]:
        assert c["sourceId"] and c["title"] and c["url"] and c["excerpt"]


@ac("AC07.2")
def test_hallucinated_citation_is_removed(client):
    a = ask(client, RAG_Q)
    assert "[c99]" not in a["answer"]
    assert "c99" not in {c["id"] for c in a["citations"]}


@ac("AC07.2")
def test_cited_chunks_were_retrieved_for_this_turn(client, db):
    a = ask(client, RAG_Q, context={"country": "JP"})
    chunk_ids = {c["chunkId"] for c in a["citations"]}
    owners = chunk_country(db)
    assert chunk_ids and all(owners[i] == "JP" for i in chunk_ids)
    logged = db.execute("SELECT cited_chunk_ids FROM chat_logs WHERE id = %s", (a["messageId"],)).fetchone()[0]
    assert set(logged) == chunk_ids


# ── US08 — Từ chối khi thiếu nguồn ──
@ac("AC08.1", "AC08.2")
def test_refuses_when_no_evidence(client, db):
    a = ask(client, "Phong tục cưới hỏi của người Maasai ở Kenya như thế nào?", context={"country": "KE"})
    assert a["confidence"] == "insufficient"
    assert "chưa có đủ nguồn" in a["answer"].lower()
    assert a["citations"] == []
    row = db.execute("SELECT type FROM feedback WHERE target_type = 'chat_message' AND target_id = %s", (a["messageId"],)).fetchone()
    assert row and row[0] == "unanswered"


# ── US09 — Ngữ cảnh trang ──
@ac("AC09.1")
def test_page_context_filters_retrieval(client, db):
    a = ask(client, "Có nên tặng hoa cúc không?", context={"country": "JP"})
    owners = chunk_country(db)
    assert all(owners[c["chunkId"]] == "JP" for c in a["citations"]), "không được lấy chunk Việt Nam khi đang xem Nhật Bản"


# ── US10 — Gợi ý & đánh giá ──
@ac("AC10.1")
def test_follow_up_questions(client):
    a = ask(client, RAG_Q)
    assert 2 <= len(a["followUpQuestions"]) <= 3


@route("POST", "/api/ai/chat/messages/{id}/rating")
@ac("AC10.2")
def test_rating_once_only(client, db):
    mid = ask(client, RAG_Q)["messageId"]
    r = client.post(f"/api/ai/chat/messages/{mid}/rating", json={"rating": 1})
    assert r.status_code == 204
    assert db.execute("SELECT rating FROM chat_logs WHERE id = %s", (mid,)).fetchone()[0] == 1
    assert_problem(client.post(f"/api/ai/chat/messages/{mid}/rating", json={"rating": -1}), 409)


@route("POST", "/api/ai/chat/messages/{id}/rating")
@ac("AC10.2")
def test_rating_value_validated(client):
    mid = ask(client, RAG_Q)["messageId"]
    assert_problem(client.post(f"/api/ai/chat/messages/{mid}/rating", json={"rating": 0}), 400)


# ── Hội thoại tự nhiên, nhiều lượt, mức giải thích (AC06.4–AC06.7) ──
@ac("AC06.4")
@pytest.mark.parametrize("message", ["Xin chào", "Bạn là ai?", "cảm ơn bạn nhé"])
def test_smalltalk_answered_naturally_without_citations(client, fake_llm, message):
    a = ask(client, message)
    assert a["route"] == "smalltalk" and a["confidence"] == "none"
    assert a["citations"] == [] and "[c" not in a["answer"] and a["answer"]
    assert fake_llm.calls and "BẰNG CHỨNG" not in fake_llm.calls[-1]["messages"][-1]["content"]
    assert 2 <= len(a["followUpQuestions"]) <= 3


@ac("AC06.5")
def test_follow_up_question_uses_previous_turn(client, db, fake_llm):
    first = ask(client, RAG_Q)
    second = ask(client, "Còn hoa thì sao?", sessionId=first["sessionId"])
    assert second["sessionId"] == first["sessionId"]
    assert second["countries"] == ["JP"], "câu nối tiếp phải hiểu là vẫn đang nói về Nhật Bản"
    owners = chunk_country(db)
    assert second["citations"] and all(owners[c["chunkId"]] == "JP" for c in second["citations"])
    history = [m["content"] for m in fake_llm.calls[-2]["messages"]]   # lượt stream của câu thứ hai
    assert RAG_Q in history, "LLM phải nhận lượt hỏi trước làm ngữ cảnh"


@ac("AC06.5")
def test_other_clients_session_history_is_not_read(client, fake_llm):
    first = ask(client, RAG_Q)
    r = client.post("/api/ai/chat", json={"message": "Còn hoa thì sao?", "sessionId": first["sessionId"]},
                    headers={**JSON, "X-Client-Id": "khach-khac-0001"})
    assert r.status_code == 200 and r.json()["sessionId"] != first["sessionId"]
    assert all(RAG_Q not in m["content"] for m in fake_llm.calls[-2]["messages"])


@ac("AC06.6")
def test_deep_level_requests_deeper_analysis(client, fake_llm):
    ask(client, RAG_Q, level="simple")
    simple = fake_llm.calls[-2]["messages"][-1]["content"]
    ask(client, RAG_Q, level="deep")
    deep = fake_llm.calls[-2]["messages"][-1]["content"]
    assert "ngắn gọn" in simple and "CHUYÊN SÂU" in deep
    assert deep.count("[c") >= simple.count("[c")


@ac("AC06.7")
def test_chat_works_with_keyword_search_when_local_ai_down(client, fake_local_ai):
    fake_local_ai.down = True          # embedding + rerank đều lỗi
    a = ask(client, "Vì sao người Nhật cúi chào?")
    assert a["route"] == "rag" and a["citations"]


# ── Loại bằng chứng (AC07.4) ──
@ac("AC07.4")
def test_reference_document_cited_with_kind_and_capped_confidence(client):
    a = ask(client, "temiyage?", context={"country": "JP"})
    assert a["citations"], a
    c = a["citations"][0]
    assert c["kind"] == "reference" and c["verified"] is False
    assert c["license"] == "CC BY-SA 4.0" and c["url"].startswith("https://en.wikipedia.org/")
    assert a["confidence"] == "inferred", "chỉ dựa trên tài liệu chưa biên tập thì không được 'supported'"


@ac("AC07.4")
def test_verified_claims_give_supported_confidence(client, fake_llm):
    fake_llm.answer = "Ở Nhật Bản, quà thường được trao bằng hai tay [c1]."
    a = ask(client, "Người Nhật trao quà bằng mấy tay?", context={"country": "JP"})
    assert a["citations"][0]["kind"] == "claim" and a["citations"][0]["verified"] is True
    assert a["confidence"] == "supported"


# ── Ngữ cảnh trang + nhận diện quốc gia (AC09.2) ──
@ac("AC09.2")
def test_structured_question_uses_page_context(client, fake_llm):
    a = ask(client, "Thủ đô là gì?", context={"country": "JP"})
    assert a["route"] == "structured" and "Tokyo" in a["answer"] and fake_llm.calls == []


@ac("AC09.2")
@pytest.mark.parametrize("message", ["Phương pháp học ngoại ngữ hiệu quả?", "Sinh nhật nên tổ chức thế nào?"])
def test_common_words_not_mistaken_for_countries(client, message):
    a = ask(client, message)
    assert a["countries"] == []


# ── Viết lại truy vấn, nhiều quốc gia, ngoài phạm vi (AC06.5, AC09.3, AC08.4) ──
@ac("AC06.5", "AC09.3")
def test_follow_up_is_rewritten_into_standalone_search_query(client, fake_llm):
    first = ask(client, RAG_Q)
    fake_llm.json["search_queries"] = {"queries": ["flower gift etiquette Japan"]}
    ask(client, "Còn hoa thì sao?", sessionId=first["sessionId"])
    rewrite_call = next(c for c in reversed(fake_llm.calls) if c.get("name") == "search_queries")
    prompt = rewrite_call["messages"][-1]["content"]
    assert RAG_Q in prompt and "Còn hoa thì sao?" in prompt, "bước viết lại phải thấy lượt trước để hiểu câu nối tiếp"


@ac("AC09.3")
def test_multi_country_question_gets_evidence_from_each_country(client, db):
    a = ask(client, "So sánh tặng quà ở Việt Nam và Nhật Bản")
    assert a["countries"] == ["VN", "JP"]
    owners = chunk_country(db)
    assert {owners[c["chunkId"]] for c in a["citations"]} == {"VN", "JP"}, "mỗi nước phải có ít nhất một bằng chứng"


@ac("AC08.4")
def test_out_of_scope_question_is_politely_refused(client):
    a = ask(client, "Giá bitcoin hôm nay bao nhiêu?")
    assert a["route"] == "refused" and a["confidence"] == "insufficient" and a["citations"] == []
    assert "chưa có đủ nguồn" in a["answer"].lower() and "10 quốc gia" in a["answer"]
