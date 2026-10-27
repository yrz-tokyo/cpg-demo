#!/usr/bin/env python3
"""eval_{label}.json から集計を出し直す（再採点後の確定値を作るため）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DEPTS = ("営業", "財務", "マーケ", "横断")
TYPES = ("scalar", "ranking", "boolean", "explanation")


def rows(label):
    p = BASE / f"eval_{label}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def pct(rs, pred):
    n = len(rs)
    k = sum(1 for r in rs if pred(r))
    return f"{k}/{n}" + (f" ({100.0*k/n:.0f}%)" if n else "")


def report(label):
    rs = rows(label)
    if not rs:
        return
    ok = lambda r: r.get("value_ok") is True            # noqa: E731
    src = lambda r: r.get("source_ok") is True          # noqa: E731
    conf = [r for r in rs if r.get("conflict")]
    nonconf = [r for r in rs if not r.get("conflict")]
    core = [r for r in rs if r.get("score_type") in ("scalar", "ranking")]
    aux = [r for r in rs if r.get("score_type") in ("boolean", "explanation")]
    print(f"\n# {label}  （{len(rs)}問 / 再採点 {sum(1 for r in rs if r.get('rescored'))}問）")
    print(f"  全体 正答率        : {pct(rs, ok)}")
    print(f"  全体 正本参照率     : {pct(rs, src)}")
    print(f"  罠を踏んだ         : {pct(rs, lambda r: r.get('trap_hit') is True)}")
    print(f"  聞き返し・拒否      : {pct(rs, lambda r: r.get('clarified') is True)}")
    print(f"  ── 主軸（scalar + ranking {len(core)}問）")
    print(f"     正答率          : {pct(core, ok)}")
    print(f"  ── 参考（boolean + explanation {len(aux)}問）")
    print(f"     正答率          : {pct(aux, ok)}")
    print(f"  ── 衝突あり {len(conf)}問")
    print(f"     正答率          : {pct(conf, ok)}")
    print(f"     正本参照率       : {pct(conf, src)}")
    print(f"  ── 衝突なし {len(nonconf)}問")
    print(f"     正答率          : {pct(nonconf, ok)}")
    print("  ── 部門別")
    for d in DEPTS:
        print(f"     {d:5s}        : {pct([r for r in rs if r.get('dept') == d], ok)}")
    print("  ── 種類別")
    for t in TYPES:
        print(f"     {t:12s}  : {pct([r for r in rs if r.get('score_type') == t], ok)}")


if __name__ == "__main__":
    for lbl in (sys.argv[1:] or ["before", "after"]):
        report(lbl)
