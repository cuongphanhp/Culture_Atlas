"""AI Cultural Guide — điều phối một lượt hỏi đáp:
phiên + lịch sử → router (smalltalk | structured | rag) → truy xuất bằng chứng → LLM stream (lọc trích dẫn) → gợi ý → ghi log.

Sự kiện trả ra (dùng cho SSE và JSON): ("token", {"text"}) … rồi ("final", ChatAnswer).
Agent tự mở kết nối DB ngắn hạn cho từng giai đoạn (không giữ kết nối suốt thời gian stream).
"""
from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.ai.citation_verifier import CitationStreamFilter, finalize
from app.ai.llm_adapter import LLMAdapter, LLMUnavailable
from app.ai.query_rewriter import rewrite
from app.ai.retrieval import (
    Embedder,
    Evidence,
    Reranker,
    is_strong,
    merge_evidence,
    retrieve,
)
from app.ai.router import (
    Country,
    Route,
    classify,
    find_countries,
    load_countries,
    structured_answer,
)
from app.ai.suggestions import (
    CATEGORY_VI,
    available_categories,
    interests_of,
    suggest,
)
from app.ai.text import fold
from app.ai.vector_store import VectorSearch
from app.core.config import get_settings
from app.core.db import get_engine

PROMPTS = Path(__file__).parent / "prompts"
SYSTEM_PROMPT = (PROMPTS / "system_vi.txt").read_text(encoding="utf-8")
SMALLTALK_PROMPT = (PROMPTS / "smalltalk_vi.txt").read_text(encoding="utf-8")

LEVELS = {
    "simple": ("Trả lời ngắn gọn 2–4 câu, từ ngữ đơn giản, dễ hiểu cho người mới.", 4),
    "normal": ("Trả lời 1–3 đoạn ngắn, đủ ý chính và lý do.", 6),
    "deep": (("Trả lời CHUYÊN SÂU nhưng chỉ trong phạm vi bằng chứng: bối cảnh/lý do hình thành, ý nghĩa, cách thực hành, "
             "khác biệt theo vùng/thế hệ, ngoại lệ và lưu ý. Chia thành vài mục ngắn có tiêu đề in đậm."), 8),
}
KIND_LABEL = {"claim": "đã biên tập", "reference": "tài liệu tham khảo", "heritage": "dữ liệu di sản UNESCO"}
FOLLOW_UP_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["questions"],
                    "properties": {"questions": {"type": "array", "items": {"type": "string"}}}}


@dataclass
class ChatInput:
    """Một lượt hỏi từ API (đã chuẩn hoá)."""

    message: str
    client_key: str
    session_id: str | None = None
    level: str = "normal"
    lang: str = "vi"
    context_country: str | None = None
    context_category: str | None = None     # mục người dùng đang xem (vd. food_dining) → chủ đề quan tâm hàng đầu


@dataclass
class Plan:
    """Kết quả bước chuẩn bị: phiên, lịch sử, tuyến xử lý, quốc gia, bằng chứng — đầu vào của `ChatAgent.run`."""

    inp: ChatInput
    session_id: str
    new_session: bool
    history: list[tuple[str, str]]
    route: Route
    countries: list[Country]
    evidence: list[Evidence] = field(default_factory=list)
    static_text: str | None = None          # câu trả lời không cần LLM (structured / từ chối)
    queries: list[str] = field(default_factory=list)
    available: set[str] = field(default_factory=set)   # chủ đề có dữ liệu cho quốc gia chính (lọc câu hỏi gợi ý)
    started: float = field(default_factory=time.perf_counter)

    @property
    def asked(self) -> list[str]:
        """Các câu người dùng đã hỏi trong phiên, cũ → mới, kể cả câu hiện tại."""
        return [q for q, _ in self.history] + [self.inp.message]


def _suggestions(plan: Plan, n: int = 3) -> list[str]:
    """Câu hỏi gợi ý từ ngân hàng câu hỏi: theo quốc gia đang nói tới và chủ đề người dùng quan tâm (AC10.3, AC10.4)."""
    iso = plan.countries[0].iso2 if plan.countries else None
    return [s.text for s in suggest(iso, plan.asked, n=n, available=plan.available,
                                    countries=[c.iso2 for c in plan.countries], focus=plan.inp.context_category)]


def _refusal(countries: list[Country]) -> str:
    if not countries:
        return ("Kho dữ liệu của mình hiện **chưa có đủ nguồn** để trả lời câu hỏi này — mình chuyên về văn hoá, phong tục, "
                "lễ hội và di sản của 10 quốc gia nên không muốn đoán ngoài phạm vi đó. Bạn thử hỏi về một nước cụ thể nhé, "
                "ví dụ “Tặng quà ở Nhật Bản cần lưu ý gì?”.")
    about = ", ".join(c.name_vi for c in countries)
    return (f"Kho dữ liệu của mình hiện **chưa có đủ nguồn** đã kiểm chứng để trả lời câu hỏi này về {about}, "
            "nên mình không muốn đoán. Bạn có thể tham khảo trang du lịch chính thức của quốc gia đó, website UNESCO "
            "hoặc bảo tàng quốc gia. Mình đã ghi lại câu hỏi để biên tập viên bổ sung nội dung.")


def _evidence_block(evidence: list[Evidence]) -> str:
    lines = [f"[{e.label}] ({KIND_LABEL.get(e.kind, e.kind)}) {e.title} — {e.publisher}: {e.text}" for e in evidence]
    return "BẰNG CHỨNG:\n" + "\n".join(lines)


class ChatAgent:
    """Điều phối một lượt hỏi đáp. Mọi phụ thuộc truyền vào để test thay bằng bản giả (tests/fakes.py)."""

    def __init__(self, llm: LLMAdapter, embedder: Embedder, local_ai: Reranker, vstore: VectorSearch | None = None) -> None:
        self.llm, self.embedder, self.local_ai, self.vstore = llm, embedder, local_ai, vstore

    # ── chuẩn bị (trước khi stream) ──
    async def prepare(self, inp: ChatInput) -> Plan:
        """Đọc phiên + lịch sử, nhận diện quốc gia, phân tuyến, truy xuất bằng chứng (song song với viết lại truy vấn)."""
        s = get_settings()
        async with get_engine().begin() as conn:
            session_id, new_session, history = await self._session(conn, inp)
            all_countries = await load_countries(conn)
            in_msg = find_countries(inp.message, all_countries)
            by_iso = {c.iso2: c for c in all_countries}
            countries = list(in_msg)
            if inp.context_country and inp.context_country in by_iso and inp.context_country not in [c.iso2 for c in countries]:
                countries.insert(0, by_iso[inp.context_country])
            if not countries and history:                       # câu hỏi nối tiếp: "còn quà thì sao?"
                for q, _ in reversed(history):
                    countries = find_countries(q, all_countries)
                    if countries:
                        break

            # Câu hỏi dữ kiện không nêu tên nước ("Thủ đô là gì?") → dùng quốc gia của ngữ cảnh / lượt trước
            route_countries = in_msg if in_msg or not route_uses_context(inp.message) else countries[:1]
            route = classify(inp.message, route_countries)
            plan = Plan(inp, session_id, new_session, history, route, countries)
            if countries:
                plan.available = await available_categories(conn, countries[0].iso2)
            if route.kind == "structured":
                plan.static_text = await structured_answer(conn, route, all_countries)
                if plan.static_text is None:
                    plan.route = Route("rag", countries)
            if plan.route.kind == "rag":
                query = inp.message
                if history and len(inp.message.split()) <= 8:
                    query = f"{history[-1][0]} {inp.message}"
                k = LEVELS.get(inp.level, LEVELS["normal"])[1]
                isos = [c.iso2 for c in countries]
                # Song song: LLM viết lại câu hỏi thành truy vấn tìm kiếm độc lập TRONG LÚC tìm bằng câu gốc.
                # Câu gốc đã cho bằng chứng mạnh → dùng luôn (không chờ viết lại); yếu → tìm thêm bằng truy vấn viết lại rồi gộp.
                rewrite_task = asyncio.create_task(rewrite(self.llm, inp.message, history, countries))
                try:
                    plan.queries = [query]
                    plan.evidence = await retrieve(conn, self.embedder, self.local_ai, query, isos, k, self.vstore)
                    if is_strong(plan.evidence, isos, s.rag_strong_score):
                        rewrite_task.cancel()
                    else:
                        rewritten = await rewrite_task
                        if rewritten:
                            plan.queries = rewritten + [query]
                            more = await retrieve(conn, self.embedder, self.local_ai, rewritten, isos, k, self.vstore)
                            plan.evidence = merge_evidence(plan.evidence, more, isos, k)
                finally:
                    if not rewrite_task.done():
                        rewrite_task.cancel()
                if not plan.evidence:
                    plan.route = Route("refused", countries)
                    plan.static_text = _refusal(countries)
        return plan

    async def _session(self, conn: AsyncConnection, inp: ChatInput) -> tuple[str, bool, list[tuple[str, str]]]:
        """→ (session_id, phiên mới?, lịch sử [(hỏi, đáp)] cũ → mới). Phiên của khách khác → tạo phiên mới."""
        sid, owned = await _owned_session(conn, inp.session_id, inp.client_key)
        if sid and owned:
            rows = (await conn.execute(text("""SELECT question, COALESCE(answer, '') FROM chat_logs WHERE session_id = :id
                                               ORDER BY created_at DESC, id DESC LIMIT :n"""),
                                       {"id": sid, "n": get_settings().chat_history_turns})).all()
            return sid, False, [(q, a) for q, a in reversed(rows)]
        return str(uuid.uuid4()), True, []

    # ── sinh câu trả lời ──
    async def run(self, plan: Plan) -> AsyncIterator[tuple[str, dict]]:
        """Sinh câu trả lời: ("token", {text})… rồi ("final", ChatAnswer). Lọc nhãn trích dẫn bịa, ghi chat_logs."""
        route = plan.route.kind
        valid = {e.label for e in plan.evidence}
        filt = CitationStreamFilter(valid)
        parts: list[str] = []
        model = route if route in ("structured", "refused") else None

        if plan.static_text is not None:
            parts.append(plan.static_text)
            yield "token", {"text": plan.static_text}
        else:
            messages = self._messages(plan)
            async for chunk in self.llm.stream(messages):
                out = filt.feed(chunk)
                if out:
                    parts.append(out)
                    yield "token", {"text": out}
            tail = filt.flush()
            if tail:
                parts.append(tail)
                yield "token", {"text": tail}
            model = getattr(self.llm, "last_model", None) or getattr(self.llm, "model", "llm")

        verified = finalize("".join(parts), valid, filt.dropped)
        cited = [e for e in plan.evidence if e.label in verified.cited_labels]
        if route == "structured":
            confidence = "supported"
        elif route == "smalltalk":
            confidence = "none"
        elif route == "refused" or (not cited and "chưa có đủ nguồn" in verified.answer.lower()):
            confidence = "insufficient"
        elif cited and all(e.verified for e in cited) and not verified.unsupported:
            confidence = "supported"
        else:
            confidence = "inferred"

        follow_ups = await self._follow_ups(plan, verified.answer) if route == "rag" else _suggestions(plan)
        message_id = await self._persist(plan, verified.answer, route, cited, confidence, model)
        yield "final", {
            "messageId": message_id, "sessionId": plan.session_id, "answer": verified.answer,
            "citations": [e.citation() for e in cited], "confidence": confidence, "route": route,
            "followUpQuestions": follow_ups[:3], "unsupportedPoints": verified.unsupported,
            "countries": [c.iso2 for c in plan.countries], "model": model,
        }

    def _messages(self, plan: Plan) -> list[dict[str, str]]:
        inp = plan.inp
        lang = "\nTrả lời bằng tiếng Anh." if inp.lang == "en" else ""
        if plan.route.kind == "smalltalk":
            msgs = [{"role": "system", "content": SMALLTALK_PROMPT + lang}]
        else:
            msgs = [{"role": "system", "content": SYSTEM_PROMPT + lang}]
        for q, a in plan.history:
            msgs += [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
        if plan.route.kind == "smalltalk":
            msgs.append({"role": "user", "content": inp.message})
        else:
            level = LEVELS.get(inp.level, LEVELS["normal"])[0]
            scope = f"\nQuốc gia đang nói tới: {', '.join(c.name_vi for c in plan.countries)}." if plan.countries else ""
            msgs.append({"role": "user", "content": f"{_evidence_block(plan.evidence)}\n\nYÊU CẦU: {level}{scope}\n\n"
                                                    f"CÂU HỎI: {inp.message}"})
        return msgs

    async def _follow_ups(self, plan: Plan, answer: str) -> list[str]:
        """3 câu hỏi tiếp theo do LLM viết, bám quốc gia + chủ đề người dùng quan tâm; LLM lỗi → lấy từ ngân hàng câu hỏi."""
        bank = _suggestions(plan, n=4)
        names = ", ".join(c.name_vi for c in plan.countries)
        topics = ", ".join(CATEGORY_VI.get(c, c) for c in interests_of(plan.asked, plan.inp.context_category)[:2])
        rules = ("Gợi ý đúng 3 câu hỏi tiếp theo (tiếng Việt tự nhiên, mỗi câu ≤ 14 từ) mà người dùng có thể muốn hỏi tiếp. "
                 + (f"Mọi câu phải về {names} và nêu tên nước hoặc một nét văn hoá cụ thể của nước đó — không viết câu chung "
                    "chung dùng được cho nước nào cũng được. " if names else "")
                 + (f"Người dùng đang quan tâm: {topics}. Hai câu đầu đào sâu chủ đề này, câu thứ ba mở sang một chủ đề "
                    "khác của cùng quốc gia. " if topics else "")
                 + "Không lặp lại câu đã hỏi. Chỉ hỏi điều mà câu trả lời hoặc các câu gợi ý mẫu cho thấy có thể có nguồn.")
        try:
            out = await self.llm.complete_json([
                {"role": "system", "content": rules},
                {"role": "user", "content": "Đã hỏi:\n" + "\n".join(f"- {q}" for q in plan.asked[-4:])
                                            + f"\n\nCâu trả lời: {answer[:1500]}"
                                            + ("\n\nCâu gợi ý mẫu (có nguồn trong kho):\n" + "\n".join(f"- {q}" for q in bank)
                                               if bank else "")}],
                name="follow_ups", schema=FOLLOW_UP_SCHEMA)
            asked = {fold(q) for q in plan.asked}
            qs = [q.strip() for q in out.get("questions", []) if isinstance(q, str) and q.strip() and fold(q) not in asked]
            if len(qs) < 2:
                return bank[:3]
            return (qs + [q for q in bank if q not in qs])[:3]
        except (LLMUnavailable, KeyError, ValueError, TypeError):
            return bank[:3]

    async def _persist(self, plan: Plan, answer: str, route: str, cited: list[Evidence], confidence: str, model: str | None) -> int:
        async with get_engine().begin() as conn:
            if plan.new_session:
                await conn.execute(text("""INSERT INTO chat_sessions (id, anon_key, context) VALUES (:id, :k, CAST(:ctx AS jsonb))
                                           ON CONFLICT (id) DO NOTHING"""),
                                   {"id": plan.session_id, "k": plan.inp.client_key,
                                    "ctx": '{"country": %s}' % (f'"{plan.inp.context_country}"' if plan.inp.context_country else "null")})
            mid = (await conn.execute(text("""
                INSERT INTO chat_logs (session_id, question, answer, language, route, cited_chunk_ids, confidence, model, latency_ms)
                VALUES (:sid, :q, :a, :lang, :route, :cids, :conf, :model, :lat) RETURNING id"""), {
                "sid": plan.session_id, "q": plan.inp.message, "a": answer, "lang": plan.inp.lang, "route": route,
                "cids": [e.chunk_id for e in cited], "conf": confidence, "model": (model or "")[:80],
                "lat": int((time.perf_counter() - plan.started) * 1000)})).scalar_one()
            if route == "refused":                      # AC08.2: đưa câu hỏi vào hàng đợi biên tập
                await conn.execute(text("""INSERT INTO feedback (target_type, target_id, type, comment)
                                           VALUES ('chat_message', :id, 'unanswered', :c)"""),
                                   {"id": mid, "c": plan.inp.message[:1000]})
        return mid


async def _owned_session(conn: AsyncConnection, session_id: str | None, client_key: str) -> tuple[str | None, bool]:
    """Chuẩn hoá `session_id` (UUID) → (id hợp lệ hoặc None, phiên có thuộc `client_key` không)."""
    if not session_id:
        return None, False
    try:
        sid = str(uuid.UUID(session_id))
    except ValueError:
        return None, False
    row = (await conn.execute(text("SELECT anon_key FROM chat_sessions WHERE id = :id"), {"id": sid})).first()
    if row is None:
        return sid, False
    return sid, row[0] == client_key


async def session_questions(conn: AsyncConnection, session_id: str | None, client_key: str, limit: int = 10) -> list[str]:
    """Các câu đã hỏi trong phiên (cũ → mới), chỉ khi phiên thuộc đúng khách; ngược lại → []."""
    sid, owned = await _owned_session(conn, session_id, client_key)
    if not owned:
        return []
    rows = (await conn.execute(text("""SELECT question FROM chat_logs WHERE session_id = :id
                                       ORDER BY created_at DESC, id DESC LIMIT :n"""), {"id": sid, "n": limit})).all()
    return [r[0] for r in reversed(rows)]


def route_uses_context(message: str) -> bool:
    """Câu hỏi dữ kiện không nêu tên nước ("Thủ đô là gì?") thì dùng quốc gia của ngữ cảnh trang."""
    from app.ai.router import STRUCTURED
    from app.ai.text import fold
    m = fold(message)
    return any(p.search(m) for _, p in STRUCTURED)
