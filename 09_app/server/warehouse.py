"""SQL warehouse への問い合わせ。Statement Execution API を薄く包むだけ。"""
from __future__ import annotations

import time
from typing import Any

from . import config


def query(sql: str, timeout_s: int = 120) -> list[dict[str, Any]]:
    w = config.workspace()
    res = w.statement_execution.execute_statement(
        statement=sql, warehouse_id=config.WAREHOUSE_ID,
        catalog=config.CATALOG, wait_timeout="30s", on_wait_timeout="CONTINUE")
    deadline = time.time() + timeout_s
    while res.status and res.status.state and res.status.state.value in ("PENDING", "RUNNING"):
        if time.time() > deadline:
            raise TimeoutError(f"SQL がタイムアウトしました: {sql[:120]}")
        time.sleep(1.5)
        res = w.statement_execution.get_statement(res.statement_id)
    state = res.status.state.value if res.status and res.status.state else "UNKNOWN"
    if state != "SUCCEEDED":
        msg = res.status.error.message if (res.status and res.status.error) else state
        raise RuntimeError(f"SQL が失敗しました: {msg}")
    cols = [c.name for c in (res.manifest.schema.columns or [])] if res.manifest else []
    rows = (res.result.data_array or []) if res.result else []
    return [dict(zip(cols, r)) for r in rows]
