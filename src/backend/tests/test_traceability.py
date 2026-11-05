"""Giữ bộ test đồng bộ với tài liệu.

1. Mọi tiêu chí ACxx.y trong docs/06-acceptance-criteria.md phải có ít nhất 1 test (backend @ac(...) hoặc frontend "[ACxx.y]").
2. Test không được tham chiếu mã AC không còn tồn tại (tài liệu đổi mà test không đổi).
3. Mọi endpoint trong docs/api/openapi.yaml phải có ít nhất 1 test khai báo @route(...).
Thêm AC hoặc endpoint mới mà chưa viết test → test này FAIL.
"""
import re
from pathlib import Path

from tests.conftest import BACKEND, REPO

AC_DOC = REPO / "docs/06-acceptance-criteria.md"
OPENAPI = REPO / "docs/api/openapi.yaml"
FRONTEND_SRC = REPO / "src/frontend/src"
AI_LOCAL_TESTS = REPO / "src/ai-local/tests"
AC_RE = re.compile(r"AC\d{2}\.\d+")

# AC không kiểm được bằng unit/API test → ghi rõ nơi kiểm chứng
EXEMPT: dict[str, str] = {}


def _doc_acs() -> set[str]:
    return set(re.findall(r"\b(AC\d{2}\.\d+)\b", AC_DOC.read_text(encoding="utf-8")))


def _backend_acs() -> dict[str, list[str]]:
    """Test Python có @ac(...) / @pytest.mark.ac(...): backend + dịch vụ AI local."""
    out: dict[str, list[str]] = {}
    for p in [*(BACKEND / "tests").rglob("test_*.py"), *AI_LOCAL_TESTS.rglob("test_*.py")]:
        if p.name == Path(__file__).name:
            continue
        for args in re.findall(r"@(?:pytest\.mark\.)?ac\(([^)]*)\)", p.read_text(encoding="utf-8")):
            for a in AC_RE.findall(args):
                out.setdefault(a, []).append(p.name)
    return out


def _frontend_acs() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in FRONTEND_SRC.rglob("*.spec.ts"):
        for a in re.findall(r"\[(AC\d{2}\.\d+)\]", p.read_text(encoding="utf-8")):
            out.setdefault(a, []).append(p.name)
    return out


def _openapi_operations() -> set[tuple[str, str]]:
    ops, path = set(), None
    for line in OPENAPI.read_text(encoding="utf-8").splitlines():
        if m := re.match(r"^  (/\S*):\s*$", line):
            path = m.group(1)
        elif path and (m := re.match(r"^    (get|post|put|patch|delete):", line)):
            ops.add((m.group(1).upper(), "/api" + path))
        elif re.match(r"^\S", line):
            path = None
    return ops


def _tested_routes() -> set[tuple[str, str]]:
    found = set()
    for p in (BACKEND / "tests").rglob("test_*.py"):
        found |= set(re.findall(r'route\("(\w+)",\s*"([^"]+)"\)', p.read_text(encoding="utf-8")))
    return found


def _norm(p: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", p)


def test_every_acceptance_criterion_has_a_test():
    covered = _backend_acs().keys() | _frontend_acs().keys() | EXEMPT.keys()
    missing = sorted(_doc_acs() - covered)
    assert not missing, f"Tiêu chí chưa có test: {missing}. Viết test với @ac(...) (backend) hoặc '[ACxx.y]' (frontend)."


def test_tests_reference_existing_criteria():
    doc = _doc_acs()
    stale = {a: files for a, files in (_backend_acs() | _frontend_acs()).items() if a not in doc}
    assert not stale, f"Test tham chiếu AC không có trong tài liệu: {stale}"


def test_every_api_operation_has_a_test():
    tested = {(m, _norm(p)) for m, p in _tested_routes()}
    missing = sorted(f"{m} {p}" for m, p in _openapi_operations() if (m, _norm(p)) not in tested)
    assert not missing, f"Endpoint trong OpenAPI chưa có test: {missing}"


def test_every_implemented_endpoint_is_documented():
    """Chiều ngược lại: endpoint đã code phải có trong docs/api/openapi.yaml (hợp đồng với frontend)."""
    from tests.conftest import _app_routes
    documented = {(m, _norm(p)) for m, p in _openapi_operations()}
    internal = {("GET", "/api/health")}
    missing = sorted(f"{m} {p}" for m, p in _app_routes() - internal if (m, _norm(p)) not in documented)
    assert not missing, f"Endpoint đã code nhưng chưa có trong OpenAPI: {missing}"


def test_openapi_is_parsed():
    assert len(_openapi_operations()) >= 30
