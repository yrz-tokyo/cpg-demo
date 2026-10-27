#!/usr/bin/env python3
"""
eval_{label}.json に質問文と Genie の回答文を後から入れる。

run_eval.py に question / genie_text / genie_sql を書かせるようにしたのは、
最初の before を回した後だった。その1回分だけテキスト証跡から補完する。
以降の実行では run_eval.py が最初から書くので、このスクリプトは不要になる。

使い方: python3 04_eval/backfill_text.py before
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent


def main(label: str) -> int:
    jp = BASE / f"eval_{label}.json"
    tp = BASE.parent / "evidence" / f"eval_{label}.txt"
    if not (jp.exists() and tp.exists()):
        print(f"ファイルがありません: {jp} / {tp}")
        return 1
    rows = json.loads(jp.read_text(encoding="utf-8"))
    txt = tp.read_text(encoding="utf-8")
    bank = {q["id"]: q for q in
            json.loads((BASE / "question_bank.json").read_text(encoding="utf-8"))["questions"]}

    blocks = {}
    for m in re.finditer(r"^## \[([A-Z\-0-9]+)\]", txt, re.M):
        qid = m.group(1)
        nxt = txt.find("\n## [", m.end())
        blocks[qid] = txt[m.end():(nxt if nxt > 0 else len(txt))]

    filled = 0
    for r in rows:
        blk = blocks.get(r["id"], "")
        if not r.get("question"):
            q = bank.get(r["id"])
            if q:
                r["question"] = q["q"]
                r["authoritative"] = q["authoritative"]
        if not r.get("genie_text"):
            m = re.search(r"^Genie 回答: (.*?)(?=^Genie 生成SQL:|^参照オブジェクト:|\Z)",
                          blk, re.M | re.S)
            if m:
                r["genie_text"] = m.group(1).strip()
                filled += 1
        if not r.get("genie_sql"):
            m = re.search(r"^Genie 生成SQL: (.*?)(?=^参照オブジェクト:|\Z)", blk, re.M | re.S)
            if m:
                r["genie_sql"] = m.group(1).strip()
    jp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{label}: {len(rows)} 行 / 回答文を補完 {filled} 件 -> {jp}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "before"))
