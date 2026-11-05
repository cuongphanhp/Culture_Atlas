"""Lỗi theo RFC 7807 (application/problem+json). Lỗi validate → 400; vi phạm nghiệp vụ → 422."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

PROBLEM_BASE = "https://cultureatlas.example/problems/"


class ProblemError(Exception):
    def __init__(self, status: int, title: str, detail: str | None = None, slug: str | None = None) -> None:
        super().__init__(title)
        self.status, self.title, self.detail, self.slug = status, title, detail, slug


def problem(status: int, title: str, detail: str | None = None, slug: str | None = None,
            errors: dict | None = None) -> JSONResponse:
    body: dict = {"type": PROBLEM_BASE + (slug or str(status)), "title": title, "status": status}
    if detail:
        body["detail"] = detail
    if errors:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def install(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def _problem(_: Request, e: ProblemError):
        return problem(e.status, e.title, e.detail, e.slug)

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, e: RequestValidationError):
        errors: dict[str, list[str]] = {}
        for err in e.errors():
            errors.setdefault(".".join(str(p) for p in err["loc"]), []).append(err["msg"])
        return problem(400, "Yêu cầu không hợp lệ", slug="validation", errors=errors)

    @app.exception_handler(HTTPException)
    async def _http(_: Request, e: HTTPException):
        return problem(e.status_code, str(e.detail))
