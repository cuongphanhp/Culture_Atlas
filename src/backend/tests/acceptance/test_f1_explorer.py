"""F1 — Cultural Explorer: Content API (US01–US05, US14). Không gọi LLM."""
import time

import pytest

from tests.conftest import ac, assert_problem, route

pytestmark = pytest.mark.db
CATEGORIES = {"greetings", "etiquette", "food_dining", "gift_giving", "festivals", "religion_beliefs",
              "clothing", "arts_music", "family_life", "heritage", "business_culture", "taboos"}


# ── US01 — Bản đồ ──
@route("GET", "/api/countries")
@ac("AC01.1")
def test_countries_list_has_coverage(client):
    r = client.get("/api/countries")
    assert r.status_code == 200
    items = {c["iso2"]: c for c in r.json()}
    assert len(items) == 10
    assert all(isinstance(c["coverage"], int) and 0 <= c["coverage"] <= 100 for c in items.values())
    assert items["JP"]["name"] == "Nhật Bản" and items["JP"]["coverage"] > 0


@route("GET", "/api/countries")
@ac("AC01.2")
def test_country_without_content_has_zero_coverage(client):
    items = {c["iso2"]: c for c in client.get("/api/countries").json()}
    assert items["KE"]["coverage"] == 0


# ── US02 — Hồ sơ quốc gia ──
@route("GET", "/api/countries/{iso}")
@ac("AC02.1", "AC01.1")
def test_country_profile(client):
    r = client.get("/api/countries/JP")
    assert r.status_code == 200
    p = r.json()
    assert p["capital"] == "Tokyo" and p["languages"] and p["currencies"]
    assert {c["code"] for c in p["categories"]} == CATEGORIES
    assert len(p["firstTimeTips"]) <= 5
    assert all(t["sourceIds"] for t in p["firstTimeTips"]), "mỗi điều cần biết phải có nguồn"


@route("GET", "/api/countries/{iso}")
@ac("AC02.1")
def test_country_profile_case_insensitive_and_404(client):
    assert client.get("/api/countries/jp").status_code == 200
    assert_problem(client.get("/api/countries/ZZ"), 404)


@route("GET", "/api/countries/{iso}/entries")
@ac("AC02.2")
def test_entries_filtered_by_category_published_only(client):
    r = client.get("/api/countries/JP/entries", params={"category": "gift_giving"})
    assert r.status_code == 200
    assert [e["id"] for e in r.json()] == [1]
    all_ids = {e["id"] for e in client.get("/api/countries/JP/entries").json()}
    assert all_ids == {1, 2}, "bài draft (3) và in_review (5) không được lộ ra"


@route("GET", "/api/countries/{iso}/entries")
@ac("AC02.2")
def test_empty_category_returns_empty_list(client):
    r = client.get("/api/countries/KE/entries", params={"category": "taboos"})
    assert r.status_code == 200 and r.json() == []


# ── US03 — Claim có phạm vi và nguồn ──
@route("GET", "/api/entries/{id}")
@ac("AC03.1", "AC03.2", "AC03.3")
def test_entry_claims_have_scope_confidence_sources(client):
    r = client.get("/api/entries/1")
    assert r.status_code == 200
    e = r.json()
    assert {c["id"] for c in e["claims"]} == {1, 2, 3}, "claim draft/unverified (4) không được hiển thị"
    for c in e["claims"]:
        assert c["scope"] in {"common_practice", "historical_tradition", "regional", "community_specific"}
        assert c["confidence"] in {"verified", "partially_supported"}
        assert c["sources"] and all(s["evidenceExcerpt"] for s in c["sources"])
    for s in e["sources"]:
        assert s["publisher"] and s["title"] and s["license"] and s["retrievedAt"]


@route("GET", "/api/entries/{id}")
@ac("AC02.2")
@pytest.mark.parametrize("entry_id", [3, 5, 999])
def test_unpublished_or_missing_entry_is_404(client, entry_id):
    assert_problem(client.get(f"/api/entries/{entry_id}"), 404)


@route("GET", "/api/sources/{id}")
@ac("AC03.2")
def test_source_detail(client):
    s = client.get("/api/sources/1").json()
    assert s["publisher"] == "Japan National Tourism Organization"
    assert s["license"] and s["retrievedAt"] == "2026-10-01" and s["reliabilityTier"] == "official"


# ── US04 — Di sản UNESCO ──
@route("GET", "/api/heritage")
@ac("AC04.1")
def test_heritage_filter_by_country_and_type(client):
    jp = client.get("/api/heritage", params={"country": "JP"}).json()
    assert {h["unescoId"] for h in jp} == {"WHC-688", "ICH-00869"}
    ich = client.get("/api/heritage", params={"country": "JP", "type": "intangible"}).json()
    assert [h["unescoId"] for h in ich] == ["ICH-00869"]
    h = ich[0]
    assert h["name"] and h["listType"] == "Representative List" and h["inscribedYear"] == 2013 and h["countries"] == ["JP"]


@route("GET", "/api/heritage")
@ac("AC04.2")
def test_heritage_attribution_cc_by_sa(client):
    for h in client.get("/api/heritage", params={"country": "JP"}).json():
        assert "CC BY-SA 4.0" in h["attribution"]


# ── US05 — Tìm kiếm ──
@route("GET", "/api/search")
@ac("AC05.1")
def test_search_without_diacritics(client):
    r = client.get("/api/search", params={"q": "nhat ban"})
    assert r.status_code == 200
    assert any(i["kind"] == "country" and i["countryIso"] == "JP" for i in r.json()["items"])


@route("GET", "/api/search")
@ac("AC05.1")
def test_search_finds_published_entries_only(client):
    items = client.get("/api/search", params={"q": "tang qua"}).json()["items"]
    entry_ids = {i["id"] for i in items if i["kind"] == "entry"}
    assert {"1", "4"} <= {str(x) for x in entry_ids}
    assert "3" not in {str(x) for x in entry_ids}


@route("GET", "/api/search")
@ac("AC05.1")
def test_search_query_too_short(client):
    assert_problem(client.get("/api/search", params={"q": "a"}), 400)


@route("GET", "/api/search")
@ac("AC05.2")
def test_search_p95_under_500ms(client):
    times = []
    for _ in range(20):
        t = time.perf_counter()
        client.get("/api/search", params={"q": "nhat ban tang qua"})
        times.append(time.perf_counter() - t)
    assert sorted(times)[18] < 0.5


# ── US14 — Báo cáo sai ──
@route("POST", "/api/feedback")
@ac("AC14.1", "AC14.2")
def test_create_feedback(client, db):
    r = client.post("/api/feedback", json={"targetType": "claim", "targetId": 2, "type": "stereotype", "comment": "Khái quát hoá quá mức."})
    assert r.status_code == 201
    fb = r.json()
    assert fb["status"] == "open" and fb["id"]
    assert db.execute("SELECT status, type FROM feedback WHERE id = %s", (fb["id"],)).fetchone() == ("open", "stereotype")


@route("POST", "/api/feedback")
@ac("AC14.1")
@pytest.mark.parametrize("payload", [
    {"targetType": "claim", "targetId": 2, "type": "other", "comment": "x" * 1001},
    {"targetType": "claim", "targetId": 2, "type": "unanswered"},       # loại nội bộ, người dùng không gửi được
    {"targetType": "planet", "targetId": 2, "type": "other"},
])
def test_invalid_feedback_rejected(client, payload):
    assert_problem(client.post("/api/feedback", json=payload), 400)


# ── Chủ đề & lễ hội (F1.7, F1.8) ──
@route("GET", "/api/themes")
def test_themes_endpoint(client):
    r = client.get("/api/themes")
    assert r.status_code == 200 and isinstance(r.json(), list)


@route("GET", "/api/festivals")
def test_festivals_by_month(client):
    assert client.get("/api/festivals", params={"month": 2}).status_code == 200
    assert_problem(client.get("/api/festivals", params={"month": 13}), 400)
