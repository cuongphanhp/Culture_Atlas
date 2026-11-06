"""Smoke test: /api/health trả ok (không cần DB)."""
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import _app_routes, _norm_path, route


def test_health() -> None:
    assert TestClient(app).get("/api/health").json() == {"status": "ok"}


@route("GET", "/api/health")
def test_test_harness_client_and_seed(client, db) -> None:
    """Kiểm tra hạ tầng test: client + DB seed hoạt động, endpoint có thật thì test được chạy."""
    assert client.get("/api/health").status_code == 200
    assert db.execute("SELECT count(*) FROM countries").fetchone()[0] == 10


def test_pending_detection_normalizes_path_params() -> None:
    assert _norm_path("/api/countries/{iso}") == _norm_path("/api/countries/{iso2}")
    assert ("GET", "/api/health") in _app_routes()
