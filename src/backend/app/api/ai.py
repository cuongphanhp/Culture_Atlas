"""AI API.
- POST /chat (SSE mặc định; Accept: application/json → một ChatAnswer), POST /chat/messages/{id}/rating
- GET /suggestions — câu hỏi gợi ý theo quốc gia + chủ đề người dùng quan tâm (không gọi LLM, không tính lượt)
- POST /compare — so sánh 2 nước × 1 chủ đề (app/services/comparison_service.py)
- Giọng nói: POST /transcribe, POST /speech, GET /voices (dịch vụ AI local)"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.ai.agent import ChatAgent, ChatInput, session_questions
from app.ai.llm_adapter import LLMAdapter, LLMUnavailable, get_llm
from app.ai.local_ai import (
    LocalAIClient,
    LocalAIError,
    LocalAIUnavailable,
    get_local_ai,
)
from app.ai.retrieval import Embedder, get_embedder
from app.ai.router import find_countries, load_countries
from app.ai.suggestions import available_categories, interests_of, suggest
from app.ai.vector_store import VectorSearch, get_vector_store
from app.core.config import get_settings
from app.core.db import get_db, get_engine
from app.core.errors import ProblemError
from app.core.rate_limit import client_key, consume
from app.schemas.ai import CategoryCode, ChatRequest, RatingRequest, SuggestionsResponse
from app.schemas.compare import CompareRequest, Comparison
from app.services import comparison_service

router = APIRouter()
LocalAI = Annotated[LocalAIClient, Depends(get_local_ai)]


def _llm_down(e: Exception) -> ProblemError:
    return ProblemError(503, "AI Guide tạm thời không phản hồi",
                        "Dịch vụ AI đang gián đoạn, bạn thử lại sau ít phút nhé. Câu hỏi dữ kiện vẫn trả lời được.", "llm-unavailable")


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


@router.post("/chat")
async def chat(body: ChatRequest, request: Request, llm: Annotated[LLMAdapter, Depends(get_llm)],
               embedder: Annotated[Embedder, Depends(get_embedder)], local: LocalAI,
               vstore: Annotated[VectorSearch, Depends(get_vector_store)]) -> Response:
    """Hỏi AI Guide (trừ 1 lượt). Mặc định stream SSE (token… rồi final); `Accept: application/json` → một ChatAnswer.

    Lỗi LLM trước khi có chữ đầu tiên → 503 RFC 7807; lỗi giữa chừng → sự kiện SSE `error`.
    """
    key = client_key(request)
    remaining = await consume(key)
    agent = ChatAgent(llm, embedder, local, vstore)
    inp = ChatInput(body.message.strip(), key, body.sessionId, body.level, body.lang,
                    body.context.country.upper() if body.context and body.context.country else None,
                    body.context.category if body.context else None)
    plan = await agent.prepare(inp)
    events = agent.run(plan)
    try:                                    # lấy sự kiện đầu trước khi trả response → lỗi LLM thành 503 đúng chuẩn
        first = await anext(events)
    except LLMUnavailable as e:
        raise _llm_down(e) from e
    headers = {"X-RateLimit-Remaining": str(remaining), "Cache-Control": "no-cache"}

    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/event-stream" not in accept:
        parts = [first]
        try:
            parts += [ev async for ev in events]
        except LLMUnavailable as e:
            raise _llm_down(e) from e
        final = next(d for ev, d in parts if ev == "final")
        return JSONResponse(final, headers=headers)

    async def stream() -> AsyncIterator[bytes]:
        yield _sse(*first)
        try:
            async for ev in events:
                yield _sse(*ev)
        except LLMUnavailable:
            yield _sse("error", {"title": "AI Guide bị gián đoạn giữa chừng", "status": 503})

    return StreamingResponse(stream(), media_type="text/event-stream", headers={**headers, "X-Accel-Buffering": "no"})


@router.get("/suggestions", response_model=SuggestionsResponse)
async def suggestions(request: Request,
                      country: Annotated[str | None, Query(pattern=r"^[A-Za-z]{2}$")] = None,
                      session_id: Annotated[str | None, Query(alias="sessionId", max_length=64)] = None,
                      category: CategoryCode | None = None,
                      limit: Annotated[int, Query(ge=1, le=6)] = 4) -> dict:
    """Câu hỏi gợi ý cho lời chào / cột "Thử hỏi" (AC10.3, AC10.4).

    Quốc gia: tham số `country`, không có thì lấy nước nhắc gần nhất trong phiên. Chủ đề quan tâm: `category` (mục đang
    xem) + câu đã hỏi trong phiên `sessionId` — chỉ đọc lịch sử khi phiên thuộc đúng khách gửi (X-Client-Id).
    """
    async with get_engine().connect() as conn:
        asked = await session_questions(conn, session_id, client_key(request))
        all_countries = await load_countries(conn)
        known = {c.iso2 for c in all_countries}
        mentioned: list[str] = []
        for q in reversed(asked):                                 # nước nhắc gần nhất đứng đầu
            mentioned += [c.iso2 for c in find_countries(q, all_countries) if c.iso2 not in mentioned]
        iso = country.upper() if country and country.upper() in known else (mentioned[0] if mentioned else None)
        available = await available_categories(conn, iso) if iso else set()
    items = suggest(iso, asked, n=limit, available=available, countries=mentioned, focus=category)
    return {"country": iso, "interests": interests_of(asked, category)[:3], "questions": [s.to_dict() for s in items]}


@router.post("/compare", response_model=Comparison)
async def compare(body: CompareRequest, db: Annotated[AsyncConnection, Depends(get_db)],
                  llm: Annotated[LLMAdapter, Depends(get_llm)], embedder: Annotated[Embedder, Depends(get_embedder)],
                  local: LocalAI, vstore: Annotated[VectorSearch, Depends(get_vector_store)]) -> dict[str, Any]:
    """So sánh 2 quốc gia × 1 chủ đề (AC11). Bản đã duyệt trả từ cache; chưa có thì AI sinh bản nháp có nguồn.

    Không trừ lượt hỏi của khách: mỗi bộ (A, B, chủ đề, ngôn ngữ) chỉ gọi LLM một lần rồi dùng lại bản đã lưu.
    """
    return await comparison_service.compare(db, llm, embedder, local, vstore, body.countryA, body.countryB,
                                            body.topic, body.lang)


@router.post("/chat/messages/{message_id}/rating", status_code=204)
async def rate_message(message_id: int, body: RatingRequest) -> Response:
    """Lưu 👍/👎 (AC10.2); đã đánh giá → 409."""
    async with get_engine().begin() as conn:
        row = (await conn.execute(text("SELECT rating FROM chat_logs WHERE id = :id FOR UPDATE"), {"id": message_id})).first()
        if row is None:
            raise ProblemError(404, "Không tìm thấy câu trả lời")
        if row[0] is not None:
            raise ProblemError(409, "Câu trả lời này đã được đánh giá", slug="already-rated")
        await conn.execute(text("UPDATE chat_logs SET rating = :r WHERE id = :id"), {"r": body.rating, "id": message_id})
    return Response(status_code=204)


async def _local[T](call: Awaitable[T]) -> T:
    """Chờ lời gọi dịch vụ AI local, đổi lỗi thành ProblemError (503 khi dịch vụ chưa sẵn sàng)."""
    try:
        return await call
    except LocalAIUnavailable as e:
        raise ProblemError(503, "Tính năng giọng nói tạm thời không khả dụng", str(e), "voice-unavailable") from e
    except LocalAIError as e:
        raise ProblemError(e.status, e.title, e.detail) from e


@router.post("/transcribe")
async def transcribe(local: LocalAI, file: UploadFile = File(...)) -> dict[str, Any]:  # noqa: B008
    """Giọng nói → văn bản (STT local). Âm thanh chỉ nằm trong bộ nhớ, không lưu (AC21.3)."""
    limit = int(get_settings().voice_max_upload_mb * 1024 * 1024)
    audio = await file.read(limit + 1)
    if len(audio) > limit:
        raise ProblemError(413, "File ghi âm quá lớn", f"Tối đa {get_settings().voice_max_upload_mb:g} MB")
    if not audio:
        raise ProblemError(400, "File ghi âm rỗng")
    r = await _local(local.transcribe(audio, file.filename or "audio", file.content_type or "application/octet-stream"))
    del audio   # không lưu âm thanh người dùng (AC21.3)
    return {"text": r["text"], "segments": r.get("segments", []), "durationS": r.get("duration"), "model": r.get("model")}


class SpeechRequest(BaseModel):
    """Body của POST /api/ai/speech."""

    text: str = Field(min_length=1)
    voice: str | None = Field(default=None, max_length=80)


@router.post("/speech")
async def speech(body: SpeechRequest, local: LocalAI) -> Response:
    """Văn bản → WAV (TTS local)."""
    if len(body.text) > get_settings().voice_max_tts_chars:
        raise ProblemError(413, "Văn bản quá dài để đọc", f"Tối đa {get_settings().voice_max_tts_chars} ký tự")
    audio, headers = await _local(local.synthesize(body.text, body.voice))
    return Response(audio, media_type="audio/wav", headers=headers)


@router.get("/voices")
async def voices(local: LocalAI) -> dict[str, Any]:
    """Danh sách giọng đọc."""
    return await _local(local.voices())
