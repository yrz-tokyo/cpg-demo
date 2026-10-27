#!/usr/bin/env python3
"""
ドメインタグを「資産そのもの」に付ける。

なぜ必要か（実機で分かったこと）
  スキーマにドメインタグを付けても、配下のテーブル / ビュー / metric view には
  **継承されない**。information_schema.table_tags は 0 件のままで、
  Discover のドメイン画面も「このドメインにはアセットがありません」になる。
  当初「ドメインタグはスキーマから継承され個別資産から剥がせない」と考えていたが、
  実機は違った。資産側に直接付ける必要がある。

  さらに、パイプライン更新や metric view の再作成で**タグは落ちる**。
  Lakeflow が MV を作り直すため。だから「1回やって終わり」ではなく、
  パイプラインを回すたびに流し直す。そのためにスクリプトにしてある。

使い方
  python3 05_governance/04_asset_domain_tags.py            # 実行
  python3 05_governance/04_asset_domain_tags.py --dry-run  # SQL を出すだけ
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

PROFILE = "fe-vm-serverless-rongzi-cpg-general"
WAREHOUSE = "2e13820648d1b0bf"
CATALOG = "rongzi_catalog_dev"
PARENT = "Brickshouse Food and Beverage"

# スキーマ -> (親ドメインの値, subdomain タグ, subdomain の値)
PLACEMENT = {
    "master_core":    ("master",           None,              None),
    "master_mart":    ("master",           None,              None),
    "sales_core":     ("sales",            f"{PARENT}/営業",   "営業"),
    "sales_mart":     ("sales",            f"{PARENT}/営業",   "営業"),
    "trade_core":     ("trade",            f"{PARENT}/営業",   "販促"),
    "trade_mart":     ("trade",            f"{PARENT}/営業",   "販促"),
    "finance_core":   ("finance",          f"{PARENT}/財務",   "財務"),
    "finance_mart":   ("finance",          f"{PARENT}/財務",   "財務"),
    "marketing_core": ("marketing",        f"{PARENT}/マーケティング", "マーケティング"),
    "marketing_mart": ("marketing",        f"{PARENT}/マーケティング", "マーケティング"),
    "procure_core":   ("procurement",      None,              None),
    "procure_mart":   ("procurement",      None,              None),
    "xdept_mart":     ("cross-department", None,              None),
}


def api(method, path, payload=None):
    cmd = ["databricks", "api", method, path, "--profile", PROFILE]
    if payload is not None:
        cmd += ["--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:400])
    return json.loads(r.stdout or "{}")


def sql(stmt: str, timeout_s: int = 120):
    res = api("post", "/api/2.0/sql/statements", {
        "statement": stmt, "warehouse_id": WAREHOUSE, "catalog": CATALOG,
        "wait_timeout": "30s", "on_wait_timeout": "CONTINUE"})
    sid = res.get("statement_id")
    deadline = time.time() + timeout_s
    while (res.get("status") or {}).get("state") in ("PENDING", "RUNNING"):
        if time.time() > deadline:
            raise TimeoutError(stmt[:100])
        time.sleep(1.2)
        res = api("get", f"/api/2.0/sql/statements/{sid}")
    st = (res.get("status") or {}).get("state")
    if st != "SUCCEEDED":
        raise RuntimeError(f"{st}: {json.dumps((res.get('status') or {}).get('error'), ensure_ascii=False)[:300]}")
    cols = [c["name"] for c in ((res.get("manifest") or {}).get("schema") or {}).get("columns", [])]
    rows = (res.get("result") or {}).get("data_array") or []
    return [dict(zip(cols, r)) for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    schemas = "', '".join(PLACEMENT)
    objs = sql(f"""
        SELECT table_schema, table_name, table_type
        FROM {CATALOG}.information_schema.tables
        WHERE table_schema IN ('{schemas}') AND table_type <> 'MANAGED'
        ORDER BY 1, 2""")
    print(f"対象オブジェクト: {len(objs)} 件")

    stmts = []
    for o in objs:
        sch, name, typ = o["table_schema"], o["table_name"], o["table_type"]
        parent_val, sub_key, sub_val = PLACEMENT[sch]
        kw = "VIEW" if typ == "METRIC_VIEW" else "TABLE"
        fq = f"`{CATALOG}`.`{sch}`.`{name}`"
        stmts.append(f"ALTER {kw} {fq} SET TAGS ('{PARENT}' = '{parent_val}');")
        if sub_key:
            stmts.append(f"ALTER {kw} {fq} SET TAGS ('{sub_key}' = '{sub_val}');")

    print(f"発行する文: {len(stmts)} 件")
    if a.dry_run:
        print("\n".join(stmts[:8]) + "\n  ...")
        return 0

    ok = err = 0
    for s in stmts:
        try:
            sql(s)
            ok += 1
        except Exception as e:
            err += 1
            print(f"  FAIL {s[:90]}\n       {str(e)[:160]}")
    print(f"\n成功 {ok} / 失敗 {err}")

    chk = sql(f"""
        SELECT tag_name, tag_value, count(*) AS n
        FROM {CATALOG}.information_schema.table_tags
        WHERE tag_name LIKE '{PARENT}%'
        GROUP BY 1, 2 ORDER BY 1, 2""")
    print("\n付与結果:")
    for r in chk:
        # count(*) は文字列で返ってくる（SQL Statement API の JSON）。int に直す。
        print(f"  {r['tag_name']:44s} = {r['tag_value']:16s} {int(r['n']):3d} 件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
