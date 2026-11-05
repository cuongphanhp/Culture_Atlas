"""AI API. Giọng nói: POST /transcribe, POST /speech, GET /voices (dịch vụ AI local).
Còn lại (P2): POST /chat (SSE), POST /chat/messages/{id}/rating, POST /compare."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.ai.local_ai import LocalAIClient, LocalAIError, LocalAIUnavailable, get_local_ai
from app.core.config import get_settings
from app.core.errors import ProblemError

router = APIRouter()
LocalAI = Annotated[LocalAIClient, Depends(get_local_ai)]


async def _local(call):
    try:
        return await call
    except LocalAIUnavailable as e:
        raise ProblemError(503, "Tính năng giọng nói tạm thời không khả dụng", str(e), "voice-unavailable") from e
    except LocalAIError as e:
        raise ProblemError(e.status, e.title, e.detail) from e


@router.post("/transcribe")
async def transcribe(local: LocalAI, file: UploadFile = File(...)):  # noqa: B008
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
    text: str = Field(min_length=1)
    voice: str | None = Field(default=None, max_length=80)


@router.post("/speech")
async def speech(body: SpeechRequest, local: LocalAI):
    if len(body.text) > get_settings().voice_max_tts_chars:
        raise ProblemError(413, "Văn bản quá dài để đọc", f"Tối đa {get_settings().voice_max_tts_chars} ký tự")
    audio, headers = await _local(local.synthesize(body.text, body.voice))
    return Response(audio, media_type="audio/wav", headers=headers)


@router.get("/voices")
async def voices(local: LocalAI):
    return await _local(local.voices())
