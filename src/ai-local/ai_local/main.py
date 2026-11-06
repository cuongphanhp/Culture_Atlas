"""HTTP API của dịch vụ AI local. Chỉ backend gọi vào (mạng nội bộ), không mở ra Internet.

    uvicorn ai_local.main:app --port 8100
"""
from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException

from ai_local.audio import STT_RATE, AudioError, decode_to_mono16k, encode_wav
from ai_local.config import settings
from ai_local.engines import Engines, EngineUnavailable


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Tạo kho model khi khởi động (test gắn sẵn engine giả vào app.state.engines); nạp sẵn nếu cấu hình."""
    if not hasattr(app.state, "engines"):
        app.state.engines = Engines()
    if settings.preload:
        app.state.engines.preload()
    yield


app = FastAPI(title="CultureAtlas AI Local", version="0.1.0", lifespan=lifespan)


def problem(status: int, title: str, detail: str | None = None) -> JSONResponse:
    """Response lỗi RFC 7807 (application/problem+json)."""
    body = {"type": f"https://cultureatlas.example/problems/{status}", "title": title, "status": status}
    if detail:
        body["detail"] = detail
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


@app.exception_handler(EngineUnavailable)
async def _unavailable(_: Request, e: EngineUnavailable) -> JSONResponse:
    return problem(503, "Model chưa sẵn sàng", str(e))


@app.exception_handler(AudioError)
async def _bad_audio(_: Request, e: AudioError) -> JSONResponse:
    return problem(400, "Âm thanh không hợp lệ", str(e))


@app.exception_handler(RequestValidationError)
async def _invalid(_: Request, e: RequestValidationError) -> JSONResponse:
    return problem(400, "Yêu cầu không hợp lệ", "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()))


@app.exception_handler(HTTPException)
async def _http(_: Request, e: HTTPException) -> JSONResponse:
    return problem(e.status_code, str(e.detail))


def engines(request: Request) -> Engines:
    """Kho model của ứng dụng."""
    return request.app.state.engines


@app.get("/health")
def health(request: Request) -> dict[str, Any]:
    """Healthcheck + model nào đã nạp."""
    return {"status": "ok", "loaded": engines(request).status()}


# ── Nhận dạng giọng nói ──
@app.post("/v1/stt")
def stt(request: Request, file: Annotated[UploadFile, File()]) -> Any:
    """Âm thanh (mọi định dạng ffmpeg đọc được) → văn bản. Âm thanh chỉ nằm trong bộ nhớ, xoá ngay sau khi giải mã."""
    data = file.file.read(int(settings.max_upload_mb * 1024 * 1024) + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        return problem(413, "File quá lớn", f"Tối đa {settings.max_upload_mb:g} MB")
    samples = decode_to_mono16k(data)
    del data                                     # không giữ âm thanh người dùng
    seconds = len(samples) / STT_RATE
    if seconds > settings.max_audio_seconds:
        return problem(413, "Đoạn ghi âm quá dài", f"Tối đa {settings.max_audio_seconds:g} giây, nhận {seconds:.0f} giây")
    return engines(request).get("stt").transcribe(samples)


# ── Đọc văn bản ──
class TTSRequest(BaseModel):
    """Body của POST /v1/tts."""

    text: str = Field(min_length=1)
    voice: str | None = None


@app.get("/v1/voices")
def voices(request: Request) -> dict[str, Any]:
    """Giọng mặc định + danh sách giọng có sẵn."""
    tts = engines(request).get("tts")
    return {"default": settings.tts_voice, "voices": tts.voices()}


@app.post("/v1/tts")
def tts(request: Request, body: TTSRequest) -> Response:
    """Văn bản → WAV; header X-Audio-Seconds, X-Elapsed-Ms, X-Voice, X-Model."""
    if len(body.text) > settings.max_tts_chars:
        return problem(413, "Văn bản quá dài", f"Tối đa {settings.max_tts_chars} ký tự")
    engine = engines(request).get("tts")
    if body.voice and not engine.has_voice(body.voice):
        return problem(400, "Giọng đọc không tồn tại", body.voice)
    t0 = time.perf_counter()
    wav = engine.synthesize(body.text, body.voice)
    elapsed = time.perf_counter() - t0
    if len(wav) == 0:
        return problem(400, "Không có nội dung để đọc")
    return Response(encode_wav(wav, engine.sample_rate), media_type="audio/wav", headers={
        "X-Audio-Seconds": f"{len(wav) / engine.sample_rate:.2f}",
        "X-Elapsed-Ms": str(int(elapsed * 1000)),
        "X-Voice": quote(body.voice or settings.tts_voice),   # header chỉ nhận latin-1
        "X-Model": engine.model,
    })


# ── Embedding & rerank (cho RAG) ──
class EmbedRequest(BaseModel):
    """Body của POST /v1/embed (tối đa 256 văn bản)."""

    texts: list[str] = Field(min_length=1, max_length=256)


@app.post("/v1/embed")
def embed(request: Request, body: EmbedRequest) -> dict[str, Any]:
    """Văn bản → vector 1024 chiều."""
    e = engines(request).get("embed")
    vectors = e.embed(body.texts)
    return {"model": e.model, "dim": int(vectors.shape[1]), "vectors": vectors.round(6).tolist()}


class RerankRequest(BaseModel):
    """Body của POST /v1/rerank."""

    query: str = Field(min_length=1)
    documents: list[str] = Field(min_length=1, max_length=100)
    top_k: int | None = Field(default=None, ge=1)


@app.post("/v1/rerank")
def rerank(request: Request, body: RerankRequest) -> dict[str, Any]:
    """Chấm độ liên quan (query, đoạn) → [{index, score}] giảm dần, cắt `top_k`."""
    r = engines(request).get("rerank")
    scores = r.score(body.query, body.documents)
    order = sorted(range(len(scores)), key=lambda i: -float(scores[i]))[: body.top_k or len(scores)]
    return {"model": r.model, "results": [{"index": i, "score": round(float(scores[i]), 5)} for i in order]}
