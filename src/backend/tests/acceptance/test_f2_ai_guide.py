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
