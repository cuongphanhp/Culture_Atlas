"""HTTP API của dịch vụ AI local. Chỉ backend gọi vào (mạng nội bộ), không mở ra Internet.

    uvicorn ai_local.main:app --port 8100
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
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
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "engines"):
        app.state.engines = Engines()
    if settings.preload:
        app.state.engines.preload()
    yield


app = FastAPI(title="CultureAtlas AI Local", version="0.1.0", lifespan=lifespan)


def problem(status: int, title: str, detail: str | None = None) -> JSONResponse:
    body = {"type": f"https://cultureatlas.example/problems/{status}", "title": title, "status": status}
    if detail:
        body["detail"] = detail
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


@app.exception_handler(EngineUnavailable)
async def _unavailable(_: Request, e: EngineUnavailable):
    return problem(503, "Model chưa sẵn sàng", str(e))


@app.exception_handler(AudioError)
async def _bad_audio(_: Request, e: AudioError):
    return problem(400, "Âm thanh không hợp lệ", str(e))


@app.exception_handler(RequestValidationError)
async def _invalid(_: Request, e: RequestValidationError):
    return problem(400, "Yêu cầu không hợp lệ", "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()))


@app.exception_handler(HTTPException)
async def _http(_: Request, e: HTTPException):
    return problem(e.status_code, str(e.detail))


def engines(request: Request) -> Engines:
    return request.app.state.engines


@app.get("/health")
def health(request: Request) -> dict:
    return {"status": "ok", "loaded": engines(request).status()}


# ── Nhận dạng giọng nói ──
@app.post("/v1/stt")
def stt(request: Request, file: UploadFile = File(...)):
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
    text: str = Field(min_length=1)
    voice: str | None = None


@app.get("/v1/voices")
def voices(request: Request):
    tts = engines(request).get("tts")
    return {"default": settings.tts_voice, "voices": tts.voices()}


@app.post("/v1/tts")
def tts(request: Request, body: TTSRequest):
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
    texts: list[str] = Field(min_length=1, max_length=256)


@app.post("/v1/embed")
def embed(request: Request, body: EmbedRequest):
    e = engines(request).get("embed")
    vectors = e.embed(body.texts)
    return {"model": e.model, "dim": int(vectors.shape[1]), "vectors": vectors.round(6).tolist()}


class RerankRequest(BaseModel):
    query: str = Field(min_length=1)
    documents: list[str] = Field(min_length=1, max_length=100)
    top_k: int | None = Field(default=None, ge=1)


@app.post("/v1/rerank")
def rerank(request: Request, body: RerankRequest):
    r = engines(request).get("rerank")
    scores = r.score(body.query, body.documents)
    order = sorted(range(len(scores)), key=lambda i: -float(scores[i]))[: body.top_k or len(scores)]
    return {"model": r.model, "results": [{"index": i, "score": round(float(scores[i]), 5)} for i in order]}
