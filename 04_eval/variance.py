#!/usr/bin/env python3
"""
同じ状態を2回測った結果を比べて、測定のばらつきを出す。

なぜ必要か
  「統治前57% → 統治後80%」と言ったとき、「それは誤差では？」に答えられないといけない。
  Genie は非決定的なので、同じ状態でも実行ごとに答えが変わる。
  統治後の状態で2回測り、その差をばらつきの目安として示す。

使い方: python3 04_eval/variance.py after after2
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent


def load(label):
    p = BASE / f"eval_{label}.json"
    if not p.exists():
        raise SystemExit(f"{p} がありません")
    return {r["id"]: r for r in json.loads(p.read_text(encoding="utf-8"))}


def rate(rows, pred):
    n = len(rows)
    k = sum(1 for r in rows if pred(r))
    return k, n, (100.0 * k / n if n else 0.0)


def main(a_label, b_label):
    a, b = load(a_label), load(b_label)
    ids = sorted(set(a) & set(b))
    print(f"同じ状態の2回測定を比較: {a_label} vs {b_label}  （共通 {len(ids)} 問）\n")

    ok = lambda r: r.get("value_ok") is True            # noqa: E731
    src = lambda r: r.get("source_ok") is True          # noqa: E731
    for name, pred in (("正答率", ok), ("正本参照率", src)):
        ka, na, pa = rate([a[i] for i in ids], pred)
        kb, nb, pb = rate([b[i] for i in ids], pred)
        print(f"  {name:10s} {ka}/{na} ({pa:.1f}%)  vs  {kb}/{nb} ({pb:.1f}%)   差 {pb - pa:+.1f} pt")

    flip = [i for i in ids if (a[i].get("value_ok") is True) != (b[i].get("value_ok") is True)]
    print(f"\n  判定が変わった問い: {len(flip)} / {len(ids)} 問 ({100.0 * len(flip) / len(ids):.1f}%)")
    for i in flip:
        va = "正解" if a[i].get("value_ok") else "不正解"
        vb = "正解" if b[i].get("value_ok") else "不正解"
        print(f"    {i:9s} [{a[i]['score_type']:11s}] {va} -> {vb}  {a[i].get('question','')[:38]}")

    print("\n  読み方: 「判定が変わった問い」の数がそのまま測定のばらつき。")
    print("  統治前後の差がこれを大きく超えていれば、差は誤差ではない。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "after",
                  sys.argv[2] if len(sys.argv) > 2 else "after2"))
