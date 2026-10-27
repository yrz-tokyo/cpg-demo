"""ペルソナ6人と、その人が実際に聞く質問。

質問は 04_eval/question_bank.json を正とする。評価で測っている質問と、
顧客に見せる質問が同じものであることが、このデモの主張の土台になる
（「測った質問をそのまま見せている」）。
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from . import config

PERSONAS = [
    {"id": "sales-head",   "dept": "営業", "role": "部長", "name": "営業本部長",
     "title": "国内営業本部 本部長",
     "asks": "部門全体の着地と、落ちている得意先がどこか。数字の出どころが揃っているか。"},
    {"id": "sales-field",  "dept": "営業", "role": "現場", "name": "営業担当",
     "title": "量販チーム 得意先担当",
     "asks": "自分の担当得意先の単票。今日なにをするか。"},
    {"id": "fin-head",     "dept": "財務", "role": "部長", "name": "経理部長",
     "title": "財務経理部 部長",
     "asks": "全社の純売上と原価率。部門が言う数字との差がどこで生まれているか。"},
    {"id": "fin-field",    "dept": "財務", "role": "現場", "name": "債権担当",
     "title": "財務経理部 売掛・販促費担当",
     "asks": "未回収と控除の明細。リーケージがどこから出ているか。"},
    {"id": "mkt-head",     "dept": "マーケ", "role": "部長", "name": "マーケ部長",
     "title": "マーケティング本部 本部長",
     "asks": "ブランド別の投資対効果と市場シェア。投下をどこへ寄せるか。"},
    {"id": "mkt-field",    "dept": "マーケ", "role": "現場", "name": "ブランド担当",
     "title": "マーケティング本部 ブランドマネージャー",
     "asks": "キャンペーンの消化率と媒体効率。止める施策と伸ばす施策。"},
]


@lru_cache(maxsize=1)
def bank() -> list[dict[str, Any]]:
    p = config.REPO / "04_eval" / "question_bank.json"
    return json.loads(p.read_text(encoding="utf-8"))["questions"]


def questions_for(persona_id: str) -> list[dict[str, Any]]:
    p = next((x for x in PERSONAS if x["id"] == persona_id), None)
    if not p:
        return []
    out = [q for q in bank() if q["dept"] == p["dept"] and q["persona"] == p["role"]]
    # 部長には横断の問いも配る。部門の壁を越える問いを持つのは部長だから。
    if p["role"] == "部長":
        out += [q for q in bank() if q["dept"] == "横断" and q["persona"] == "部長"]
    return [{"id": q["id"], "q": q["q"], "conflict": q["conflict"],
             "authoritative": q["authoritative"], "trap": q.get("trap", []),
             "score_type": q["score_type"]} for q in out]


def space_for(persona_id: str) -> str:
    p = next((x for x in PERSONAS if x["id"] == persona_id), None)
    ids = config.space_ids()
    if not p:
        return ids.get("横断", "")
    return ids.get(p["dept"]) or ids.get("横断", "")
