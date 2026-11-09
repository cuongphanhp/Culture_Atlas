"""Schema của POST /api/ai/compare (docs/api/openapi.yaml: CompareRequest, SourcedText, Comparison)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.ai import CategoryCode
from app.schemas.content import Source


class CompareRequest(BaseModel):
    """Body của POST /api/ai/compare: hai quốc gia khác nhau × một chủ đề (AC11.4)."""

    countryA: str = Field(pattern=r"^[A-Za-z]{2}$")
    countryB: str = Field(pattern=r"^[A-Za-z]{2}$")
    topic: CategoryCode
    lang: Literal["vi", "en"] = "vi"

    @model_validator(mode="after")
    def _distinct(self) -> CompareRequest:
        self.countryA, self.countryB = self.countryA.upper(), self.countryB.upper()
        if self.countryA == self.countryB:
            raise ValueError("Hãy chọn hai quốc gia khác nhau để so sánh")
        return self


class SourcedText(BaseModel):
    """Một ô có nguồn. Ô không đủ bằng chứng là null ("Chưa đủ nguồn để kết luận", AC11.2)."""

    text: str
    sourceIds: list[int] = Field(min_length=1)


class CompareRow(BaseModel):
    """Một khía cạnh so sánh: ô của nước A và nước B."""

    aspect: str
    a: SourcedText | None
    b: SourcedText | None


class Comparison(BaseModel):
    """Kết quả so sánh. `reviewed` = bản đã được biên tập viên duyệt (AC11.1); False = bản nháp AI (AC11.3)."""

    countryA: str
    countryB: str
    topic: CategoryCode
    reviewed: bool
    reviewedBy: str | None
    similarities: list[SourcedText]
    rows: list[CompareRow]
    context: str | None
    caveats: list[str]
    insufficient: list[str]
    sources: list[Source]
