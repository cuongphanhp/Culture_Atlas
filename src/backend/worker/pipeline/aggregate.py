"""Gộp bản ghi từ mọi nguồn → data/aggregated/*.json + báo cáo độ phủ (report.md)."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from worker.config import MVP_COUNTRIES

# Ưu tiên khi gộp thông tin quốc gia: nguồn đứng trước thắng, nguồn sau chỉ lấp chỗ trống.
COUNTRY_PRIORITY = ("rest_countries", "wikidata")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def merge_countries(by_source: dict[str, list[dict]]) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for src in COUNTRY_PRIORITY:
        for rec in by_source.get(src, []):
            cur = merged.setdefault(rec["iso2"], {"iso2": rec["iso2"], "sources": []})
            for k, v in rec.items():
                if k in ("provenance", "kind"):
                    continue
                if v not in (None, [], "") and cur.get(k) in (None, [], ""):
                    cur[k] = v
            cur["sources"].append(rec["provenance"])
    return merged


def aggregate(data_dir: Path) -> dict:
    norm = data_dir / "normalized"
    by_source = {p.stem: read_jsonl(p) for p in sorted(norm.glob("*.jsonl"))}
    out_dir = data_dir / "aggregated"
    out_dir.mkdir(parents=True, exist_ok=True)

    countries = merge_countries(by_source)
    heritage: dict[str, dict] = {}
    media, documents, topics = [], [], []
    for src, recs in by_source.items():
        for r in recs:
            kind = r.get("kind")
            if kind == "heritage":
                heritage.setdefault(r["unesco_id"], r)
            elif kind == "media":
                media.append(r)
            elif kind == "document":
                documents.append(r)
            elif kind == "topic":
                topics.append(r)

    for name, payload in (("countries", list(countries.values())), ("heritage", list(heritage.values())),
                          ("media", media), ("documents", documents), ("topics", topics)):
        (out_dir / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    # Ma trận độ phủ quốc gia × nguồn
    matrix: dict[str, Counter] = defaultdict(Counter)
    for src, recs in by_source.items():
        for r in recs:
            isos = [r.get("iso2") or r.get("country")] if r.get("kind") != "heritage" else r.get("countries", [])
            for iso in isos:
                if iso in MVP_COUNTRIES:  # di sản đa quốc gia: chỉ đếm cho các nước MVP
                    matrix[iso][src] += 1
    cats: dict[str, Counter] = defaultdict(Counter)
    for d in documents:
        cats[d["country"]][d.get("category_guess") or "uncategorized"] += 1

    summary = {"sources": {s: len(r) for s, r in by_source.items()}, "countries": len(countries), "heritage": len(heritage),
               "media": len(media), "documents": len(documents), "topics": len(topics),
               "matrix": {k: dict(v) for k, v in sorted(matrix.items())}, "document_categories": {k: dict(v) for k, v in cats.items()}}
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    (data_dir / "report.md").write_text(render_report(summary, data_dir), encoding="utf-8")
    return summary


def render_report(s: dict, data_dir: Path) -> str:
    srcs = sorted(s["sources"])
    lines = ["# Ingestion report", "", "| Country | " + " | ".join(srcs) + " |", "|---|" + "---|" * len(srcs)]
    for iso, row in s["matrix"].items():
        if len(iso) == 2 and iso.isupper() and any(row.values()):
            lines.append(f"| {iso} | " + " | ".join(str(row.get(x, "—")) for x in srcs) + " |")
    lines += ["", f"Totals: {s['countries']} countries · {s['heritage']} heritage items · {s['media']} media · "
              f"{s['documents']} reference documents · {s['topics']} topic suggestions", "", "## Runs", ""]
    for p in sorted((data_dir / "runs").glob("*.json"))[-20:]:
        r = json.loads(p.read_text(encoding="utf-8"))
        note = "; ".join((r.get("skipped") or []) + (r.get("errors") or []))[:180]
        lines.append(f"- `{r['source_name']}` {r['status']} · {r['records_changed']} records · {r.get('duration_s')}s {('— ' + note) if note else ''}")
    return "\n".join(lines) + "\n"
