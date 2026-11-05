"""Hạ tầng chung cho bộ test CultureAtlas AI.

Cách hoạt động (chi tiết: tests/README.md):
- Test nghiệm thu gọi HTTP API như frontend, mỗi test gắn mã tiêu chí bằng @ac("ACxx.y").
- @route("GET", "/api/...") khai báo endpoint test cần. Nếu app CHƯA có endpoint đó, test được đánh dấu
  PENDING (skip) và tự bật lại khi endpoint được code. Đặt ACCEPTANCE_STRICT=1 để PENDING thành FAIL.
- Test có dùng DB chạy trên PostgreSQL riêng (compose.test.yaml, cổng 55432), nạp lại seed trước mỗi test.
- LLM và embedding luôn là bản giả (tests/fakes.py) — bộ test không bao giờ gọi OpenAI.
"""
from __future__ import annotations

import importlib
import os
import re
import uuid
from collections import Counter
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parents[1]
SCHEMA_SQL = REPO / "src/database/culture_atlas.sql"
SEED_SQL = BACKEND / "tests/fixtures/seed.sql"

TEST_DSN = os.environ.get("TEST_DATABASE_URL", "postgresql://atlas:atlas@localhost:55432/culture_atlas_test")
ADMIN_DSN = TEST_DSN.rsplit("/", 1)[0] + "/postgres"
STRICT = os.environ.get("ACCEPTANCE_STRICT") == "1"

# Cấu hình app cho test — đặt TRƯỚC khi import app, ghi đè .env của máy dev
os.environ.update({
    "DATABASE_URL": TEST_DSN.replace("postgresql://", "postgresql+asyncpg://", 1),
    "WORKER_DATABASE_URL": TEST_DSN,
    "JWT_SECRET": "test-secret",
    "GUEST_DAILY_LIMIT": "10",
    "LLM_PROVIDER": "fake",
    "OPENAI_API_KEY": "",
    "APP_ENV": "test",
})

# Dependency của app được thay bằng bản giả: "module:hàm" → tên fixture
DEPENDENCY_OVERRIDES = {
    "app.ai.llm_adapter:get_llm": "fake_llm",
    "app.ai.retrieval:get_embedder": "fake_embedder",
    "app.ai.local_ai:get_local_ai": "fake_local_ai",
}

ac = pytest.mark.ac


def route(method: str, path: str):
    return pytest.mark.route(method.upper(), path)


# ───────────────────────── PENDING: endpoint chưa có ─────────────────────────

def _norm_path(p: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", p.rstrip("/"))


def _app_routes() -> set[tuple[str, str]]:
    """Endpoint app đang có, đọc từ OpenAPI do app sinh ra (FastAPI mới lồng router con nên app.routes không phẳng)."""
    from app.main import app
    out = set()
    for path, ops in app.openapi()["paths"].items():
        for m in ops:
            if m in {"get", "post", "put", "patch", "delete"}:
                out.add((m.upper(), _norm_path(path)))
    return out


def pytest_runtest_setup(item: pytest.Item) -> None:
    wanted = [(m.args[0], m.args[1]) for m in item.iter_markers("route")]
    if not wanted:
        return
    have = _app_routes()
    missing = [f"{m} {p}" for m, p in wanted if (m, _norm_path(p)) not in have]
    if missing:
        acs = ",".join(a for m in item.iter_markers("ac") for a in m.args)
        msg = f"PENDING [{acs}] chưa có endpoint: {', '.join(missing)}"
        if STRICT:
            pytest.fail(msg)
        pytest.skip(msg)


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    pending = [r for r in terminalreporter.stats.get("skipped", []) if "PENDING" in str(r.longrepr)]
    if not pending:
        return
    by_ac: Counter[str] = Counter()
    for r in pending:
        m = re.search(r"PENDING \[([^\]]*)\]", str(r.longrepr))
        for a in (m.group(1).split(",") if m and m.group(1) else ["(không mã)"]):
            by_ac[a] += 1
    terminalreporter.section("Tiêu chí chấp nhận đang PENDING (chưa code)")
    terminalreporter.write_line(f"{len(pending)} test chờ tính năng: " + ", ".join(f"{k}×{v}" for k, v in sorted(by_ac.items())))


# ───────────────────────── PostgreSQL test ─────────────────────────

def _unavailable(msg: str):
    if STRICT:
        pytest.fail(msg)
    pytest.skip(msg)


@pytest.fixture(scope="session")
def pg_dsn() -> str:
    import psycopg
    name = TEST_DSN.rsplit("/", 1)[1]
    try:
        admin = psycopg.connect(ADMIN_DSN, autocommit=True, connect_timeout=3)
    except Exception as e:  # noqa: BLE001
        _unavailable(f"PostgreSQL test chưa chạy ({type(e).__name__}). Chạy: docker compose -f compose.test.yaml up -d --wait")
    with admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        admin.execute(f'CREATE DATABASE "{name}"')
    with psycopg.connect(TEST_DSN, autocommit=True) as c:
        c.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
    return TEST_DSN


def _reset(conn, embedder) -> None:
    tables = [r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")]
    conn.execute(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE")
    conn.execute(SEED_SQL.read_text(encoding="utf-8"))
    # Chunk RAG cho mọi claim đã xuất bản (một claim = một chunk), embedding bằng FakeEmbedder
    rows = conn.execute("""
        SELECT cl.id, cl.text, e.id, e.category, c.iso2 FROM claims cl
        JOIN culture_entries e ON e.id = cl.entry_id JOIN countries c ON c.id = e.country_id
        WHERE cl.status = 'published' AND e.status = 'published' ORDER BY cl.id""").fetchall()
    for claim_id, text, entry_id, category, iso in rows:
        vec = "[" + ",".join(f"{v:.6f}" for v in embedder.embed_one(text)) + "]"
        conn.execute(
            """INSERT INTO entry_chunks (entry_id, claim_ids, chunk_text, language, metadata, embedding)
               VALUES (%s, %s, %s, 'vi', %s, %s::vector)""",
            (entry_id, [claim_id], text, f'{{"country": "{iso}", "category": "{category}", "entry_id": {entry_id}}}', vec))


@pytest.fixture
def fake_embedder():
    from tests.fakes import FakeEmbedder
    return FakeEmbedder()


@pytest.fixture
def fake_local_ai():
    from tests.fakes import FakeLocalAI
    return FakeLocalAI()


@pytest.fixture
def fake_llm():
    from tests.fakes import FakeLLM
    return FakeLLM()


@pytest.fixture
def db(pg_dsn, fake_embedder):
    """Kết nối autocommit tới DB test vừa nạp lại seed — dùng để kiểm tra trạng thái sau khi gọi API."""
    import psycopg
    conn = psycopg.connect(pg_dsn, autocommit=True)
    _reset(conn, fake_embedder)
    yield conn
    conn.close()


# ───────────────────────── HTTP client ─────────────────────────

@pytest.fixture
def client(request, db):
    """TestClient của app với LLM/embedding giả. Mỗi test là một khách riêng (header X-Client-Id)."""
    from fastapi.testclient import TestClient

    from app.main import app
    for target, fixture_name in DEPENDENCY_OVERRIDES.items():
        mod_name, attr = target.split(":")
        try:
            dep = getattr(importlib.import_module(mod_name), attr)
        except (ImportError, AttributeError):
            continue  # chưa có trong app — test cần nó sẽ PENDING theo @route
        fake = request.getfixturevalue(fixture_name)
        app.dependency_overrides[dep] = (lambda f: lambda: f)(fake)   # không dùng tham số mặc định: FastAPI sẽ coi là query param và deepcopy
    with TestClient(app, headers={"X-Client-Id": uuid.uuid4().hex}) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def login(client):
    """login("editor") → header Authorization cho tài khoản seed tương ứng."""
    def _login(role: str) -> dict[str, str]:
        r = client.post("/api/auth/login", json={"email": f"{role}@test.local", "password": "Passw0rd!"})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['accessToken']}"}
    return _login


def assert_problem(resp, status: int | tuple[int, ...]) -> dict:
    """Lỗi phải theo RFC 7807: đúng mã, Content-Type application/problem+json, có type/title/status."""
    statuses = status if isinstance(status, tuple) else (status,)
    assert resp.status_code in statuses, f"{resp.status_code} {resp.text[:300]}"
    assert resp.headers["content-type"].startswith("application/problem+json"), resp.headers["content-type"]
    body = resp.json()
    assert {"type", "title", "status"} <= body.keys() and body["status"] == resp.status_code
    return body
