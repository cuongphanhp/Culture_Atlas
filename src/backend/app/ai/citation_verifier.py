"""Kiểm tra trích dẫn: mỗi [c#] phải trỏ tới bằng chứng đã truy xuất cho lượt hỏi này (AC07.2).

- CitationStreamFilter: lọc ngay khi stream — nhãn bịa (ví dụ [c99]) không bao giờ tới tay người dùng.
- finalize(): sau khi có toàn văn → danh sách trích dẫn thật sự dùng, câu chứa nhãn bịa, mức tin cậy.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

MARKER = re.compile(r"\[(c\d+)\]")


class CitationStreamFilter:
    """Nhận từng mẩu văn bản, trả phần an toàn để gửi ngay; giữ lại phần "[c…" chưa đóng cho tới khi đủ để quyết định."""

    def __init__(self, valid: set[str]) -> None:
        self.valid = valid
        self.buf = ""
        self.dropped: list[str] = []

    def _clean(self, s: str) -> str:
        """Bỏ nhãn [c#] không có trong bằng chứng, ghi lại vào `dropped`."""
        def repl(m: re.Match) -> str:
            if m.group(1) in self.valid:
                return m.group(0)
            self.dropped.append(m.group(1))
            return ""
        return MARKER.sub(repl, s)

    def feed(self, chunk: str) -> str:
        """Nhận một mẩu từ LLM → phần đã an toàn để gửi ngay cho người dùng."""
        self.buf += chunk
        cut = self.buf.rfind("[")
        if cut != -1 and "]" not in self.buf[cut:] and len(self.buf) - cut <= 8:
            ready, self.buf = self.buf[:cut], self.buf[cut:]       # có thể là đầu một nhãn [c12] — chờ thêm
        else:
            ready, self.buf = self.buf, ""
        return self._clean(ready)

    def flush(self) -> str:
        """Hết stream → trả nốt phần còn giữ lại."""
        ready, self.buf = self.buf, ""
        return self._clean(ready)


@dataclass
class Verified:
    """Câu trả lời đã làm sạch + nhãn thực sự trích dẫn + các câu mất nguồn (unsupportedPoints)."""

    answer: str
    cited_labels: list[str]
    unsupported: list[str] = field(default_factory=list)


def tidy(answer: str) -> str:
    """Dọn khoảng trắng thừa sau khi bỏ nhãn trích dẫn."""
    answer = re.sub(r"[ \t]+([.,;:!?])", r"\1", answer)        # khoảng trắng còn lại sau khi bỏ nhãn
    answer = re.sub(r"[ \t]{2,}", " ", answer)
    return answer.strip()


def finalize(answer: str, valid: set[str], dropped: list[str]) -> Verified:
    """Nhãn hợp lệ theo thứ tự xuất hiện; câu từng chứa nhãn bịa được ghi vào unsupportedPoints."""
    cited = list(dict.fromkeys(m for m in MARKER.findall(answer) if m in valid))
    clean = tidy(MARKER.sub(lambda m: m.group(0) if m.group(1) in valid else "", answer))
    unsupported = []
    if dropped:
        for sent in re.split(r"(?<=[.!?])\s+", clean):
            if sent.strip() and not MARKER.search(sent) and len(sent.split()) > 3:
                unsupported.append(sent.strip())
    return Verified(clean, cited, unsupported[:5])
