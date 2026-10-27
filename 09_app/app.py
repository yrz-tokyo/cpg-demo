"""Brickshouse データ統治コックピット — API。

3画面ぶんのエンドポイントを持つ。
  ① /api/personas, /api/ask          … ペルソナ別に聞いて、引用元つきで答える（顧客デモ）
  ② /api/conflicts, /api/decide      … 衝突を人が裁いて Lakebase に書き戻す（両方）
  ③ /api/eval                        … 統治前/後の同じ質問の変化（FE Bar）

認可は必ずここで判断する。画面のラベルを信じない。
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from server import config, evalstore, genie, personas, review, warehouse

HERE = Path(__file__).resolve().parent
DIST = HERE / "frontend" / "dist"

app = FastAPI(title="Brickshouse データ統治コックピット")


def signed_in(request: Request) -> str:
    """画面の前にいる人。Apps がヘッダで入れてくる。ローカルでは CLI の自分。"""
    who = (request.headers.get("x-forwarded-email")
           or request.headers.get("x-forwarded-user"))
    if who:
        return who
    try:
        return config.workspace().current_user.me().user_name or "local"
    except Exception:
        return "local"


def reviewers() -> list[str]:
    """衝突を裁ける人。画面ではなくここで決める。空なら誰でも可（デモ既定）。"""
    return [v.strip().lower() for v in os.getenv("CONFLICT_REVIEWERS", "").split(",") if v.strip()]


# ---------------------------------------------------------------- ① ペルソナ

@app.get("/api/personas")
def api_personas():
    return {"personas": [{**p, "questions": personas.questions_for(p["id"]),
                          "space_id": personas.space_for(p["id"])}
                         for p in personas.PERSONAS]}


class AskBody(BaseModel):
    persona_id: str
    question: str = Field(min_length=2, max_length=600)


@app.post("/api/ask")
def api_ask(body: AskBody):
    space = personas.space_for(body.persona_id)
    if not space:
        raise HTTPException(503, "Genie Agent が未設定です（06_genie/space_ids.json）")
    got = genie.ask(space, body.question)
    if got.get("error"):
        raise HTTPException(502, got["error"])
    return {**got, "citations": citations(got.get("refs", []))}


_CITE_CACHE: dict[str, dict] = {}


def citations(refs: list[str]) -> list[dict]:
    """引用されたオブジェクトの認定状態とコメントを返す。答えの根拠を画面に出すため。"""
    out = []
    for ref in refs:
        if ref in _CITE_CACHE:
            out.append(_CITE_CACHE[ref]); continue
        sch, _, obj = ref.partition(".")
        try:
            rows = warehouse.query(f"""
                SELECT t.table_schema, t.table_name, t.comment,
                       (SELECT tag_value FROM {config.CATALOG}.information_schema.table_tags g
                         WHERE g.schema_name=t.table_schema AND g.table_name=t.table_name
                           AND g.tag_name='system.certification_status') AS certification,
                       (SELECT tag_value FROM {config.CATALOG}.information_schema.schema_tags s
                         WHERE s.schema_name=t.table_schema
                           AND s.tag_name='brickshouse_department') AS department
                FROM {config.CATALOG}.information_schema.tables t
                WHERE t.table_schema='{sch}' AND t.table_name='{obj}' LIMIT 1""")
        except Exception:
            rows = []
        item = {"ref": ref,
                "comment": (rows[0].get("comment") if rows else None),
                "certification": (rows[0].get("certification") if rows else None),
                "department": (rows[0].get("department") if rows else None)}
        _CITE_CACHE[ref] = item
        out.append(item)
    return out


# ---------------------------------------------------------------- ② 衝突レビュー

@app.get("/api/conflicts")
def api_conflicts():
    try:
        return {"conflicts": review.conflicts(), "labels": review.labels()}
    except Exception as e:
        raise HTTPException(503, f"Lakebase に接続できません: {e}")


class DecideBody(BaseModel):
    conflict_id: int
    decision: str
    authoritative_object: str | None = None
    rationale: str = Field(default="", max_length=2000)
    # 検出器(LLM)が付けた業務用語を人が直せるようにする
    term: str | None = Field(default=None, max_length=60)


@app.post("/api/decide")
def api_decide(body: DecideBody, request: Request):
    who = signed_in(request)
    allowed = reviewers()
    if allowed and who.lower() not in allowed:
        raise HTTPException(403, f"{who} は衝突を裁く権限がありません")
    try:
        return review.decide(body.conflict_id, body.decision,
                             body.authoritative_object, body.rationale, who,
                             term=body.term)
    except (ValueError, LookupError) as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(503, f"Lakebase への書き込みに失敗しました: {e}")


# ---------------------------------------------------------------- ③ 統治の効果

@app.get("/api/eval")
def api_eval():
    return evalstore.compare()


# ---------------------------------------------------------------- 共通

@app.get("/api/me")
def api_me(request: Request):
    return {"email": signed_in(request), "catalog": config.CATALOG,
            "spaces": config.space_ids(),
            "can_review": (not reviewers()) or signed_in(request).lower() in reviewers()}


@app.get("/api/health")
def api_health():
    return {"ok": True}


if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = DIST / path
        if path and f.is_file():
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
