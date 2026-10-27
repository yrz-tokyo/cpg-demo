"""評価結果の読み出し。

run_eval.py が書いた 04_eval/eval_{before,after}.json を読む。
テキストの再パースはしない。提出物に入る証跡と画面に出る数字を同じファイルから取ることで、
画面の数字と提出物の数字が食い違わないようにしている。
"""
from __future__ import annotations

import json
from typing import Any

from . import config

LABELS = ("before", "after")
DEPTS = ("営業", "財務", "マーケ", "横断")
TYPES = ("scalar", "ranking", "boolean", "explanation")


def _load(label: str) -> list[dict[str, Any]]:
    p = config.REPO / "04_eval" / f"eval_{label}.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def _rate(rows: list[dict], pred) -> dict[str, Any]:
    n = len(rows)
    k = sum(1 for r in rows if pred(r))
    return {"k": k, "n": n, "pct": round(100.0 * k / n, 1) if n else None}


def summary(label: str) -> dict[str, Any] | None:
    rows = _load(label)
    if not rows:
        return None
    ok = lambda r: r.get("value_ok") is True            # noqa: E731
    src = lambda r: r.get("source_ok") is True          # noqa: E731
    trap = lambda r: r.get("trap_hit") is True          # noqa: E731
    clar = lambda r: r.get("clarified") is True         # noqa: E731
    conf = [r for r in rows if r.get("conflict")]
    return {
        "label": label,
        "total": _rate(rows, ok),
        "source": _rate(rows, src),
        "trap": _rate(rows, trap),
        "clarified": _rate(rows, clar),
        "wrong_direct": _rate(rows, lambda r: r.get("value_ok") is False and not r.get("clarified")),
        "conflict": _rate(conf, ok),
        "conflict_source": _rate(conf, src),
        "by_dept": {d: _rate([r for r in rows if r.get("dept") == d], ok) for d in DEPTS},
        "by_type": {t: _rate([r for r in rows if r.get("score_type") == t], ok) for t in TYPES},
    }


def compare() -> dict[str, Any]:
    """同じ質問の before / after を1行に並べる。画面③の本体。"""
    before = {r["id"]: r for r in _load("before")}
    after = {r["id"]: r for r in _load("after")}
    ids = list(before) or list(after)
    items = []
    for qid in ids:
        b, a = before.get(qid), after.get(qid)
        src = b or a or {}
        def mv(r):
            if not r:
                return None
            if r.get("clarified"):
                return "clarified"
            return "ok" if r.get("value_ok") is True else ("ng" if r.get("value_ok") is False else None)
        items.append({
            "id": qid,
            "dept": src.get("dept"), "persona": src.get("persona"),
            "conflict": bool(src.get("conflict")),
            "question": src.get("question") or "",
            "authoritative": src.get("authoritative") or "",
            "before": {"verdict": mv(b), "text": (b or {}).get("genie_text", ""),
                       "sql": (b or {}).get("genie_sql", ""), "refs": (b or {}).get("refs", []),
                       "numbers": (b or {}).get("genie_numbers", [])},
            "after": {"verdict": mv(a), "text": (a or {}).get("genie_text", ""),
                      "sql": (a or {}).get("genie_sql", ""), "refs": (a or {}).get("refs", []),
                      "numbers": (a or {}).get("genie_numbers", [])},
            "truth": src.get("truth_numbers", []),
            "flipped": mv(b) != mv(a) and mv(a) is not None,
        })
    # 変わった質問を先に出す。変わっていないものを上に並べると何も起きていないように見える。
    items.sort(key=lambda x: (not x["flipped"], not x["conflict"], x["id"]))
    return {"before": summary("before"), "after": summary("after"), "items": items}
