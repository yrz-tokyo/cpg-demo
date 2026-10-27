"""Genie Agent に質問する。

回答・生成SQL・引用したオブジェクト・結果の3点を返す。画面では必ず引用元を出す
（AI の答えは、どこから来たかが見えないと業務では使えない）。
"""
from __future__ import annotations

import re
import time
from typing import Any

from . import config

TBL = re.compile(r"`?(\w+)`?\.`?(\w+)`?\.`?(\w+)`?")


def referenced_objects(sql: str) -> list[str]:
    if not sql:
        return []
    out = set()
    for m in TBL.finditer(sql):
        cat, sch, obj = m.groups()
        if cat == config.CATALOG:
            out.add(f"{sch}.{obj}")
    return sorted(out)


def ask(space_id: str, question: str, timeout_s: int = 180) -> dict[str, Any]:
    w = config.workspace()
    started = w.genie.start_conversation(space_id=space_id, content=question)
    cid = started.conversation_id or (started.conversation.id if started.conversation else None)
    mid = started.message_id or (started.message.id if started.message else None)
    if not (cid and mid):
        return {"error": "start_conversation の戻りが想定外"}

    deadline = time.time() + timeout_s
    msg = None
    while time.time() < deadline:
        msg = w.genie.get_message(space_id=space_id, conversation_id=cid, message_id=mid)
        st = msg.status.value if msg.status else ""
        if st in ("COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"):
            break
        time.sleep(2)
    if msg is None:
        return {"error": "タイムアウト"}

    text, sql, statement_id, desc = "", "", None, ""
    for a in (msg.attachments or []):
        if a.text and not text:
            text = a.text.content or ""
        if a.query and not sql:
            sql = a.query.query or ""
            statement_id = a.query.statement_id
            desc = a.query.description or ""

    result = None
    if statement_id:
        try:
            rr = w.statement_execution.get_statement(statement_id)
            cols = [c.name for c in (rr.manifest.schema.columns or [])] if rr.manifest else []
            rows = (rr.result.data_array or []) if rr.result else []
            result = {"columns": cols, "rows": rows[:50]}
        except Exception as e:                      # 結果は期限切れになりうる
            result = {"columns": [], "rows": [], "note": f"結果を取得できませんでした: {e}"}

    return {"status": msg.status.value if msg.status else None,
            "text": text, "description": desc, "sql": sql,
            "refs": referenced_objects(sql), "result": result,
            "conversation_id": cid, "message_id": mid}
