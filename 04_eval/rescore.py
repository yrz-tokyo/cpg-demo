#!/usr/bin/env python3
"""
保存済みの回答テキストから boolean の判定だけを作り直す。

なぜ再実行でなく再採点か
  boolean の採点に必要なのは Genie の**回答文**だけで、それは eval_{label}.json に
  保存してある。採点器のバグを直すたびに49問を回し直すのは無駄なうえ、
  Genie は非決定的なので「直した効果」と「実行ごとの揺れ」が混ざって検証できなくなる。
  **同じ回答文に対して採点だけをやり直す**ので、変化は採点器の修正だけに帰属する。

直したバグ（実測）
  偽陽性: 「判定する質問には該当しません」「判定不可」= 拒否なのに
          「該当しません」が否定語に当たって正解扱いになっていた
  偽陰性: 「含まれていません」「当社売上ではなく」= 正しい否定なのに辞書に無かった

使い方: python3 04_eval/rescore.py before after after2
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from run_eval import AFFIRM_WORDS, NEGATIVE_WORDS, REFUSAL_WORDS  # noqa: E402


def verdict(text: str, expect: bool):
    refused = any(w in text for w in REFUSAL_WORDS)
    negated = any(w in text for w in NEGATIVE_WORDS)
    affirmed = any(w in text for w in AFFIRM_WORDS)
    # 拒否が優勢なのは「方向が立たないとき」。質問文の選択肢を両方引用すると
    # 否定も肯定も当たるので、その場合も拒否として扱う。
    if refused and not (negated ^ affirmed):
        return False, "拒否（はい/いいえを答えていない）", True
    if expect:
        return (affirmed and not negated), f"肯定={affirmed} 否定={negated} / 期待=はい", False
    return (negated and not affirmed), f"否定={negated} 肯定={affirmed} / 期待=いいえ", False


def main(labels):
    bank = {q["id"]: q for q in
            json.loads((BASE / "question_bank.json").read_text(encoding="utf-8"))["questions"]}
    for label in labels:
        p = BASE / f"eval_{label}.json"
        if not p.exists():
            print(f"{label}: ファイルが無いので飛ばす")
            continue
        rows = json.loads(p.read_text(encoding="utf-8"))
        changed = []
        for r in rows:
            if r.get("score_type") != "boolean":
                continue
            q = bank.get(r["id"], {})
            exp = q.get("expect_answer")
            exp = exp if isinstance(exp, bool) else False
            text = (r.get("genie_text") or "") + " " + (r.get("genie_sql") or "")
            ok, detail, refused = verdict(text, exp)
            if r.get("value_ok") is not ok:
                changed.append((r["id"], r.get("value_ok"), ok, detail))
            r["value_ok"], r["detail"] = ok, detail
            if refused:
                r["clarified"] = True
            r["rescored"] = "boolean-v2"
        total_ok = sum(1 for r in rows if r.get("value_ok") is True)
        p.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n{label}: boolean を再採点  → 全体 {total_ok}/{len(rows)} "
              f"({100.0 * total_ok / len(rows):.0f}%)")
        for qid, was, now, detail in changed:
            print(f"   {qid}: {was} -> {now}   {detail}")
        if not changed:
            print("   判定の変化なし")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["before", "after"]))
