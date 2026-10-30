"""Content API (không gọi LLM): countries, entries, heritage, search, sources, themes, festivals, quizzes, feedback."""
from fastapi import APIRouter

router = APIRouter(tags=["Content"])
