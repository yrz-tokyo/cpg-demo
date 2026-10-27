"""衝突レビュー（画面②）。

検出された衝突候補を Lakebase から読み、人が approve / reject した結果を書き戻す。
書き戻しが ML の学習ラベルになる（semantics.ml_training_label ビュー）ので、
この画面のクリックが次回の検出順位を変える。ループが閉じる場所。
"""
from __future__ import annotations

from typing import Any

from . import lakebase

LIST_SQL = """
SELECT c.conflict_id, c.term, c.term_normalized, c.measure_name, c.status,
       c.ml_score, c.detector_version, c.detected_at, c.evidence,
       d.decision, d.authoritative_object, d.rationale, d.decided_by, d.decided_at
FROM semantics.conflict c
LEFT JOIN LATERAL (
  SELECT * FROM semantics.decision x
  WHERE x.conflict_id = c.conflict_id ORDER BY x.decided_at DESC LIMIT 1
) d ON TRUE
ORDER BY (d.decision IS NOT NULL), c.ml_score DESC NULLS LAST, c.conflict_id
"""

CAND_SQL = """
SELECT conflict_id, candidate_id, object_name, object_type, department,
       measure_expr, role, observed_value, note
FROM semantics.conflict_candidate
WHERE conflict_id = ANY(%s)
ORDER BY conflict_id, observed_value DESC NULLS LAST
"""

# ML の学習ラベル。approve -> 1 / reject -> 0 が機械的に導出される。
# この画面のクリックが、そのまま次回の検出順位の学習データになる。
LABEL_SQL = """
SELECT term_normalized, measure_name, label_is_real_conflict AS label, COUNT(*) AS n
FROM semantics.ml_training_label GROUP BY 1,2,3 ORDER BY 1,2,3
"""


def conflicts() -> list[dict[str, Any]]:
    rows = lakebase.fetch(LIST_SQL)
    if not rows:
        return []
    ids = [r["conflict_id"] for r in rows]
    cands = lakebase.fetch(CAND_SQL, (ids,))
    by_id: dict[int, list[dict]] = {}
    for c in cands:
        by_id.setdefault(c["conflict_id"], []).append(c)
    for r in rows:
        r["candidates"] = by_id.get(r["conflict_id"], [])
        r["detected_at"] = r["detected_at"].isoformat() if r.get("detected_at") else None
        r["decided_at"] = r["decided_at"].isoformat() if r.get("decided_at") else None
        r["ml_score"] = float(r["ml_score"]) if r.get("ml_score") is not None else None
        for c in r["candidates"]:
            c["observed_value"] = float(c["observed_value"]) if c.get("observed_value") is not None else None
    return rows


def labels() -> list[dict[str, Any]]:
    try:
        return lakebase.fetch(LABEL_SQL)
    except Exception:
        return []


def decide(conflict_id: int, decision: str, authoritative_object: str | None,
           rationale: str, who: str, term: str | None = None) -> dict[str, Any]:
    """1トランザクションで判断を書き、却下なら再提案抑止ペアも書く。

    term を渡すと業務用語を上書きする。検出器(LLM)が付ける言葉は当たらないことがあり
    （total_net_amount に「正味金額」と付けた）、言葉を決めるのは人の仕事なので
    画面から直せる必要がある。
    """
    if decision not in ("approve", "reject", "defer"):
        raise ValueError("decision は approve / reject / defer のみ")
    if decision == "approve" and not authoritative_object:
        raise ValueError("approve のときは正本オブジェクトが必要")

    head = lakebase.fetch(
        "SELECT term, term_normalized, measure_name FROM semantics.conflict WHERE conflict_id = %s",
        (conflict_id,))
    if not head:
        raise LookupError(f"conflict_id {conflict_id} が見つかりません")
    measure = head[0]["measure_name"]
    term = (term or "").strip() or head[0]["term"]
    norm = head[0]["term_normalized"]

    stmts: list[tuple[str, tuple]] = [
        ("""UPDATE semantics.conflict
               SET term = %s, term_normalized = lower(regexp_replace(%s, '\\s+', '', 'g')),
                   updated_at = now()
             WHERE conflict_id = %s""",
         (term, term, conflict_id)),
        ("""INSERT INTO semantics.decision
              (conflict_id, decision, authoritative_object, rationale, decided_by)
            VALUES (%s,%s,%s,%s,%s)""",
         (conflict_id, decision, authoritative_object, rationale, who)),
        ("""UPDATE semantics.conflict
               SET status = %s, updated_at = now() WHERE conflict_id = %s""",
         # status の許可値は detected / investigating / resolved / rejected。
         # 保留は investigating（まだ見ている）に寄せる。
         ("resolved" if decision == "approve" else
          ("rejected" if decision == "reject" else "investigating"), conflict_id)),
        ("""INSERT INTO app.audit_log (actor, action, target, payload)
            VALUES (%s,%s,%s, jsonb_build_object('rationale', %s::text,
                                                 'authoritative', %s::text))""",
         (who, f"conflict.{decision}", f"conflict:{conflict_id}",
          rationale, authoritative_object)),
    ]
    if decision == "reject":
        objs = lakebase.fetch(
            "SELECT object_name FROM semantics.conflict_candidate "
            "WHERE conflict_id = %s ORDER BY object_name", (conflict_id,))
        names = [o["object_name"] for o in objs]
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                stmts.append((
                    """INSERT INTO semantics.rejected_pair
                         (term_normalized, measure_name, object_a, object_b, rejected_by, reason)
                       VALUES (%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (term_normalized, measure_name, object_a, object_b)
                       DO UPDATE SET rejected_at = now(), reason = EXCLUDED.reason""",
                    (norm, measure, names[i], names[j], who, rationale)))
    lakebase.execute(stmts)
    return {"conflict_id": conflict_id, "decision": decision, "labels": labels()}
