"""F7 — Xác thực & trang quản trị (US15–US19, US20 qua API)."""
import time
from datetime import UTC, datetime, timedelta

import jwt  # PyJWT (python-jose bỏ vì không còn bảo trì, có CVE CRITICAL chưa vá)
import pytest

from tests.conftest import TEST_JWT_SECRET, ac, assert_problem, route

pytestmark = [pytest.mark.db, route("POST", "/api/auth/login")]


def poll(fn, timeout=10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if v := fn():
            return v
        time.sleep(0.2)
    return fn()


# ── US15 — Đăng nhập & phân quyền ──
@ac("AC15.1")
def test_login_success_and_failure(client):
    r = client.post("/api/auth/login", json={"email": "admin@test.local", "password": "Passw0rd!"})
    assert r.status_code == 200
    assert r.json()["accessToken"] and r.json()["user"]["role"] == "admin"
    assert_problem(client.post("/api/auth/login", json={"email": "admin@test.local", "password": "sai"}), 401)
    assert_problem(client.post("/api/auth/login", json={"email": "disabled@test.local", "password": "Passw0rd!"}), 401)


@route("GET", "/api/auth/me")
@ac("AC15.1")
def test_me(client, login):
    assert client.get("/api/auth/me", headers=login("editor")).json()["role"] == "editor"
    assert_problem(client.get("/api/auth/me"), 401)


@route("GET", "/api/admin/users")
@ac("AC15.1")
@pytest.mark.parametrize("role,status", [("admin", 200), ("editor", 403), ("learner", 403)])
def test_users_admin_only(client, login, role, status):
    r = client.get("/api/admin/users", headers=login(role))
    if status == 200:
        assert r.status_code == 200 and len(r.json()) == 4
    else:
        assert_problem(r, 403)


@route("GET", "/api/admin/users")
@ac("AC15.1")
def test_admin_requires_token(client):
    assert_problem(client.get("/api/admin/users"), 401)


@route("GET", "/api/auth/me")
@ac("AC15.2")
def test_expired_or_forged_token_rejected(client):
    past = datetime.now(UTC) - timedelta(minutes=5)
    expired = jwt.encode({"sub": "1", "role": "admin", "exp": past}, TEST_JWT_SECRET, algorithm="HS256")
    forged = jwt.encode({"sub": "1", "role": "admin", "exp": past + timedelta(hours=2)}, "khong-phai-secret", algorithm="HS256")
    for tok in (expired, forged):
        assert_problem(client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"}), 401)


@route("PATCH", "/api/admin/users/{id}")
@ac("AC15.1")
def test_admin_changes_role(client, login, db):
    r = client.patch("/api/admin/users/3", json={"role": "editor"}, headers=login("admin"))
    assert r.status_code == 200 and r.json()["role"] == "editor"
    assert_problem(client.patch("/api/admin/users/3", json={"role": "admin"}, headers=login("editor")), 403)


@route("PATCH", "/api/admin/users/{id}")
@ac("AC15.1")
def test_admin_cannot_demote_or_lock_self(client, login):
    h = login("admin")
    assert_problem(client.patch("/api/admin/users/1", json={"role": "editor"}, headers=h), 422)
    assert_problem(client.patch("/api/admin/users/1", json={"isActive": False}, headers=h), 422)
    assert_problem(client.patch("/api/admin/users/999", json={"role": "editor"}, headers=h), 404)


@route("PATCH", "/api/admin/users/{id}")
@route("GET", "/api/auth/me")
@ac("AC15.2")
def test_locked_user_token_stops_working_immediately(client, login):
    editor = login("editor")
    assert client.patch("/api/admin/users/2", json={"isActive": False}, headers=login("admin")).status_code == 200
    assert_problem(client.get("/api/auth/me", headers=editor), 401)
    assert_problem(client.post("/api/auth/login", json={"email": "editor@test.local", "password": "Passw0rd!"}), 401)


@route("GET", "/api/auth/me")
@ac("AC15.2")
def test_token_of_unknown_user_or_bad_header_rejected(client):
    future = datetime.now(UTC) + timedelta(hours=1)
    ghost = jwt.encode({"sub": "999", "role": "admin", "exp": future}, TEST_JWT_SECRET, algorithm="HS256")
    no_exp = jwt.encode({"sub": "1", "role": "admin"}, TEST_JWT_SECRET, algorithm="HS256")
    for header in (f"Bearer {ghost}", f"Bearer {no_exp}", "Bearer khong-phai-jwt"):
        assert_problem(client.get("/api/auth/me", headers={"Authorization": header}), 401)


@ac("AC15.1")
def test_login_refused_when_jwt_secret_too_short(client, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "jwt_secret", "change-me")
    assert_problem(client.post("/api/auth/login", json={"email": "admin@test.local", "password": "Passw0rd!"}), 503)


@route("POST", "/api/feedback")
@ac("AC14.2")
def test_feedback_records_logged_in_user(client, login, db):
    r = client.post("/api/feedback", json={"targetType": "entry", "targetId": 1, "type": "other"}, headers=login("learner"))
    assert r.status_code == 201
    assert db.execute("SELECT user_id FROM feedback WHERE id = %s", (r.json()["id"],)).fetchone() == (3,)


# ── US16 — Duyệt nội dung ──
@route("POST", "/api/admin/review/{targetType}/{id}/decision")
@route("GET", "/api/entries/{id}")
@ac("AC16.1")
def test_approve_entry_publishes_versions_and_reindexes(client, login, db):
    r = client.post("/api/admin/review/entry/5/decision", json={"decision": "approve"}, headers=login("editor"))
    assert r.status_code == 200 and r.json()["status"] == "published"
    assert db.execute("SELECT count(*) FROM entry_revisions WHERE entry_id = 5").fetchone()[0] >= 1
    assert poll(lambda: db.execute("SELECT count(*) FROM entry_chunks WHERE entry_id = 5").fetchone()[0], timeout=60)
    assert client.get("/api/entries/5").status_code == 200


@route("POST", "/api/admin/review/{targetType}/{id}/decision")
@ac("AC16.2")
def test_reject_requires_reason(client, login, db):
    h = login("editor")
    assert_problem(client.post("/api/admin/review/entry/5/decision", json={"decision": "reject"}, headers=h), 422)
    r = client.post("/api/admin/review/entry/5/decision", json={"decision": "reject", "reason": "Thiếu nguồn chính thức"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] != "published"


@route("POST", "/api/admin/review/{targetType}/{id}/decision")
@ac("AC15.1")
def test_learner_cannot_review(client, login):
    assert_problem(client.post("/api/admin/review/entry/5/decision", json={"decision": "approve"}, headers=login("learner")), 403)


@route("POST", "/api/admin/ai/drafts")
@route("GET", "/api/admin/review-queue")
@ac("AC16.3")
def test_ai_drafts_enter_queue_as_draft(client, login, db):
    h = login("editor")
    r = client.post("/api/admin/ai/drafts", json={"kind": "quiz", "entryIds": [1], "n": 1}, headers=h)
    assert r.status_code == 202 and r.json()["jobId"]
    assert poll(lambda: db.execute("SELECT count(*) FROM quiz_questions WHERE origin = 'ai_generated' AND id > 3").fetchone()[0])
    assert db.execute("SELECT DISTINCT status FROM quiz_questions WHERE origin = 'ai_generated' AND id > 3").fetchall() == [("draft",)]
    queue = client.get("/api/admin/review-queue", params={"origin": "ai_generated", "type": "quiz_question"}, headers=h).json()
    assert queue["total"] >= 1 and all(i["status"] == "draft" for i in queue["items"])


# ── US17 — Claim & nguồn ──
@route("POST", "/api/admin/review/{targetType}/{id}/decision")
@ac("AC17.1")
def test_cannot_publish_claim_without_source(client, login, db):
    body = assert_problem(client.post("/api/admin/review/claim/4/decision", json={"decision": "approve"}, headers=login("editor")), 422)
    assert body["title"]
    assert db.execute("SELECT status FROM claims WHERE id = 4").fetchone()[0] == "draft"


@route("POST", "/api/admin/entries/{id}/claims")
@ac("AC17.1", "AC17.2")
@pytest.mark.parametrize("sources", [[], [{"sourceId": 1}], [{"sourceId": 1, "evidenceExcerpt": ""}]])
def test_claim_requires_source_with_excerpt(client, login, sources):
    r = client.post("/api/admin/entries/1/claims", headers=login("editor"),
                    json={"text": "Một phát biểu đủ dài để kiểm tra.", "scope": "common_practice", "sources": sources})
    assert_problem(r, (400, 422))


@route("POST", "/api/admin/entries/{id}/claims")
@ac("AC17.2")
def test_add_claim_stores_evidence(client, login, db):
    r = client.post("/api/admin/entries/1/claims", headers=login("editor"), json={
        "text": "Quà thường được gói cẩn thận ở Nhật Bản.", "scope": "common_practice",
        "sources": [{"sourceId": 1, "evidenceExcerpt": "Gifts are carefully wrapped.", "locator": "§Gifts"}]})
    assert r.status_code == 201
    cid = r.json()["id"]
    assert db.execute("SELECT evidence_excerpt FROM claim_sources WHERE claim_id = %s", (cid,)).fetchone()[0] == "Gifts are carefully wrapped."
    assert db.execute("SELECT status FROM claims WHERE id = %s", (cid,)).fetchone()[0] != "published"


@route("POST", "/api/admin/entries")
@ac("AC16.3")
def test_create_entry_starts_as_draft(client, login):
    r = client.post("/api/admin/entries", headers=login("editor"),
                    json={"countryIso": "KE", "category": "greetings", "titleVi": "Chào hỏi ở Kenya"})
    assert r.status_code == 201 and r.json()["status"] == "draft"


@route("PUT", "/api/admin/entries/{id}")
@ac("AC16.1")
def test_update_entry_optimistic_lock(client, login):
    h = login("editor")
    body = {"countryIso": "JP", "category": "gift_giving", "titleVi": "Tặng quà ở Nhật Bản (sửa)"}
    assert_problem(client.put("/api/admin/entries/1", json={**body, "version": 1}, headers=h), 409)
    assert client.put("/api/admin/entries/1", json={**body, "version": 2}, headers=h).status_code == 200


# ── US18 — Nguồn & giấy phép ──
@route("POST", "/api/admin/sources")
@ac("AC18.1")
def test_source_requires_license_and_unique_url(client, login):
    h = login("editor")
    src = {"title": "Korea etiquette", "publisher": "Korea Tourism Organization", "url": "https://english.visitkorea.or.kr/etiquette",
           "sourceType": "official_site", "license": "Excerpts only", "reliabilityTier": "official", "retrievedAt": "2026-11-01"}
    assert_problem(client.post("/api/admin/sources", json={k: v for k, v in src.items() if k != "license"}, headers=h), (400, 422))
    assert client.post("/api/admin/sources", json=src, headers=h).status_code == 201
    assert_problem(client.post("/api/admin/sources", json=src, headers=h), 409)


@route("GET", "/api/admin/sources")
@ac("AC18.1")
def test_list_sources(client, login):
    assert all(s["license"] and s["retrievedAt"] for s in client.get("/api/admin/sources", headers=login("editor")).json())


# ── Báo cáo sai (US14 phía biên tập) ──
@route("GET", "/api/admin/feedback")
@route("PATCH", "/api/admin/feedback/{id}")
@ac("AC14.2")
def test_editor_handles_feedback(client, login):
    h = login("editor")
    assert [f["id"] for f in client.get("/api/admin/feedback", params={"status": "open"}, headers=h).json()] == [1]
    r = client.patch("/api/admin/feedback/1", json={"status": "resolved", "note": "Đã bổ sung nguồn"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "resolved"


# ── US19 — Độ phủ ──
@route("GET", "/api/admin/coverage")
@ac("AC19.1", "AC19.2")
def test_coverage_matrix(client, login):
    cells = {(c["iso2"], c["category"]): c["publishedClaims"] for c in client.get("/api/admin/coverage", headers=login("editor")).json()}
    assert len(cells) == 120
    assert cells[("JP", "gift_giving")] == 3 and cells[("KE", "greetings")] == 0


# ── US20 — Đồng bộ dữ liệu qua API ──
@route("GET", "/api/admin/ingestion/runs")
@route("POST", "/api/admin/ingestion/runs")
@ac("AC20.1")
def test_ingestion_runs_admin_only(client, login):
    assert client.get("/api/admin/ingestion/runs", headers=login("admin")).status_code == 200
    assert_problem(client.post("/api/admin/ingestion/runs", json={"source": "wikidata"}, headers=login("editor")), 403)


@route("GET", "/api/admin/benchmark/runs")
@ac("AC08.3")
def test_benchmark_runs_admin_only(client, login):
    assert client.get("/api/admin/benchmark/runs", headers=login("admin")).status_code == 200
    assert_problem(client.get("/api/admin/benchmark/runs", headers=login("editor")), 403)
