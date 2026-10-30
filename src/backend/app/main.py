"""Điểm vào FastAPI: gắn router Content / AI / Auth / Admin, CORS, xử lý lỗi RFC 7807."""
from fastapi import FastAPI

from app.api import admin, ai, auth, content

app = FastAPI(title="CultureAtlas AI API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.include_router(content.router, prefix="/api")
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/api/admin")


@app.get("/api/health", tags=["Ops"])
def health() -> dict[str, str]:
    return {"status": "ok"}
