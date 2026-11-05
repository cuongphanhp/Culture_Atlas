"""Quy tắc nghiệp vụ được DB đảm bảo (src/database/culture_atlas.sql) — chạy được ngay, không cần API."""
import psycopg
import pytest

from tests.conftest import ac

pytestmark = pytest.mark.db


@ac("AC17.1")
def test_claim_without_source_cannot_be_published(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("UPDATE claims SET status = 'published' WHERE id = 4")
    assert db.execute("SELECT status FROM claims WHERE id = 4").fetchone()[0] == "draft"


@ac("AC17.1")
def test_claim_with_source_can_be_published(db):
    db.execute("UPDATE claims SET status = 'published' WHERE id = 8")
    assert db.execute("SELECT status FROM claims WHERE id = 8").fetchone()[0] == "published"


@ac("AC03.1")
def test_regional_claim_requires_region(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("INSERT INTO claims (entry_id, text, scope) VALUES (1, 'Phong tục vùng miền không rõ vùng', 'regional')")


@ac("AC17.2")
def test_claim_source_link_requires_evidence_excerpt(db):
    with pytest.raises(psycopg.errors.NotNullViolation):
        db.execute("INSERT INTO claim_sources (claim_id, source_id, evidence_excerpt) VALUES (4, 1, NULL)")


@ac("AC18.1")
@pytest.mark.parametrize("column", ["license", "retrieved_at"])
def test_source_requires_license_and_retrieved_at(db, column):
    values = {"license": "'CC0'", "retrieved_at": "'2026-01-01'"}
    values[column] = "NULL"
    with pytest.raises(psycopg.errors.NotNullViolation):
        db.execute(f"""INSERT INTO sources (title, publisher, source_url, source_type, license, reliability_tier, retrieved_at)
                       VALUES ('t', 'p', 'https://x.test/{column}', 'academic', {values['license']}, 'academic', {values['retrieved_at']})""")


@ac("AC18.2")
def test_unverified_media_cannot_be_stored_locally(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("""INSERT INTO media_assets (url, stored_url, license, attribution_text, verified)
                      VALUES ('https://x.test/a.jpg', '/media/a.jpg', 'Unknown', 'x', FALSE)""")
    db.execute("""INSERT INTO media_assets (url, stored_url, license, attribution_text, verified)
                  VALUES ('https://x.test/b.jpg', NULL, 'Unknown', 'x', FALSE)""")


@ac("AC11.4")
def test_comparison_requires_two_distinct_countries(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("INSERT INTO comparisons (country_a_id, country_b_id, topic, result) VALUES (1, 1, 'greetings', '{}')")


@ac("AC14.1")
def test_feedback_comment_max_1000_chars(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("INSERT INTO feedback (target_type, target_id, type, comment) VALUES ('entry', 1, 'other', %s)", ("x" * 1001,))
    db.execute("INSERT INTO feedback (target_type, target_id, type, comment) VALUES ('entry', 1, 'other', %s)", ("x" * 1000,))


@ac("AC12.1")
def test_quiz_answer_index_within_options(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("""INSERT INTO quiz_questions (entry_id, question, options, answer_index, explanation, difficulty)
                      VALUES (1, 'q', '["a","b"]', 2, 'e', 'easy')""")


@ac("AC10.2")
def test_chat_rating_only_plus_or_minus_one(db):
    sid = db.execute("INSERT INTO chat_sessions DEFAULT VALUES RETURNING id").fetchone()[0]
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("INSERT INTO chat_logs (session_id, question, rating) VALUES (%s, 'q', 0)", (sid,))


@ac("AC05.1")
def test_fulltext_matches_vietnamese_without_diacritics(db):
    assert db.execute("SELECT to_tsvector('ca_simple', 'Tặng quà ở Nhật Bản') @@ plainto_tsquery('ca_simple', 'tang qua nhat ban')").fetchone()[0]
    hits = db.execute("SELECT entry_id FROM entry_chunks WHERE tsv @@ plainto_tsquery('ca_simple', 'hoa cuc')").fetchall()
    assert {r[0] for r in hits} == {1, 4}


@ac("AC19.1")
def test_coverage_view_counts_only_published_claims(db):
    rows = dict(((iso, cat), n) for iso, cat, n in db.execute("SELECT iso2, category::text, published_claims FROM v_coverage"))
    assert len(rows) == 10 * 12
    assert rows[("JP", "gift_giving")] == 3          # claim 4 (draft) không tính
    assert rows[("JP", "greetings")] == 0            # bài đang chờ duyệt không tính
    assert all(n == 0 for (iso, _), n in rows.items() if iso == "KE")
