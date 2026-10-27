"""実行環境の差を1か所に閉じる。

ローカル（CLI プロファイル）と Databricks Apps（注入された SP 資格情報）の両方で動かす。
WorkspaceClient はどちらも面倒を見てくれるので、分岐はプロファイル名だけ。
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent          # 09_app
REPO = BASE.parent                                     # cpg-multi-dept-genie

CATALOG = os.getenv("BRICKSHOUSE_CATALOG", "rongzi_catalog_dev")
PROFILE = os.getenv("DATABRICKS_CONFIG_PROFILE")       # Apps では未設定
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "2e13820648d1b0bf")
LAKEBASE_INSTANCE = os.getenv("LAKEBASE_INSTANCE", "brickshouse")
LAKEBASE_DB = os.getenv("LAKEBASE_DB", "databricks_postgres")
LAKEBASE_USER = os.getenv("LAKEBASE_USER", "")         # 空なら現在のプリンシパル


@lru_cache(maxsize=1)
def workspace():
    from databricks.sdk import WorkspaceClient
    return WorkspaceClient(profile=PROFILE) if PROFILE else WorkspaceClient()


@lru_cache(maxsize=1)
def space_ids() -> dict[str, str]:
    """部門 -> Genie Agent の space_id。"""
    raw = os.getenv("GENIE_SPACE_IDS", "").strip()
    if raw:
        return json.loads(raw)
    p = REPO / "06_genie" / "space_ids.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
