#!/usr/bin/env python3
"""
ダッシュボード JSON の中のデータセット SQL を、デプロイ前に全部実行して確かめる。

ダッシュボードの中では FROM にテーブル名だけを書く（catalog/schema は作成時のフラグで入る）。
検証ではここで3部名に補って実行する。実行して初めて分かる間違い（列名・型・集計の形）を
デプロイ前に潰すため。ウィジェットは SQL の出力列にそのまま結びつくので、
SQL が通らなければウィジェットは必ず壊れる。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

PROFILE = "fe-vm-serverless-rongzi-cpg-general"
WAREHOUSE = "2e13820648d1b0bf"
CATALOG = "rongzi_catalog_dev"

# データセットの SQL は `schema.table` で書く。
# ダッシュボードは複数スキーマ（sales_mart / xdept_mart / trade_mart ...）にまたがるので、
# テーブル名だけにすると --dataset-schema が1つしか渡せず解決できない。
# カタログだけを作成時のフラグから入れることで、カタログ間の可搬性は保つ。
SCHEMA_OF = {
    "mart_sales_performance": "sales_mart", "mart_account_coverage": "sales_mart",
    "mart_revenue_reconciliation": "finance_mart", "mart_standard_cost_compare": "finance_mart",
    "mart_promotion_roi": "trade_mart", "mart_trade_spend_flow": "trade_mart",
    "mart_campaign_performance": "marketing_mart", "mart_media_efficiency": "marketing_mart",
    "mart_brand_market_position": "marketing_mart",
    "mart_revenue_definitions": "xdept_mart", "mart_customer_360": "xdept_mart",
    "mart_spend_definitions": "xdept_mart", "mart_brand_investment_return": "xdept_mart",
}


def api(method, path, payload=None):
    cmd = ["databricks", "api", method, path, "--profile", PROFILE]
    if payload is not None:
        cmd += ["--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:300])
    return json.loads(r.stdout or "{}")


def run(stmt, timeout_s=120):
    res = api("post", "/api/2.0/sql/statements", {
        "statement": stmt, "warehouse_id": WAREHOUSE, "catalog": CATALOG,
        "wait_timeout": "30s", "on_wait_timeout": "CONTINUE"})
    sid = res.get("statement_id")
    deadline = time.time() + timeout_s
    while (res.get("status") or {}).get("state") in ("PENDING", "RUNNING"):
        if time.time() > deadline:
            return "TIMEOUT", None
        time.sleep(1.2)
        res = api("get", f"/api/2.0/sql/statements/{sid}")
    st = (res.get("status") or {}).get("state")
    if st != "SUCCEEDED":
        return st, json.dumps((res.get("status") or {}).get("error"), ensure_ascii=False)[:280]
    rows = (res.get("result") or {}).get("data_array") or []
    cols = [c["name"] for c in ((res.get("manifest") or {}).get("schema") or {}).get("columns", [])]
    return "OK", (cols, rows)


def qualify(sql: str) -> str:
    """検証用にカタログを補う（ダッシュボード本体では作成時のフラグが補う）。"""
    return re.sub(r"(FROM\s+|JOIN\s+)(\w+\.\w+)", lambda m: f"{m.group(1)}{CATALOG}.{m.group(2)}", sql)


def main(files):
    bad = 0
    for f in files:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        print(f"\n### {Path(f).name}")
        ds_cols = {}
        for ds in d["datasets"]:
            sql = qualify("".join(ds["queryLines"]))
            st, out = run(f"SELECT * FROM ({sql.rstrip().rstrip(';')}) x LIMIT 5")
            if st != "OK":
                print(f"  ✗ {ds['name']:22s} {st}: {out}")
                bad += 1
                continue
            cols, rows = out
            ds_cols[ds["name"]] = set(cols)
            print(f"  ✓ {ds['name']:22s} {len(cols)} 列 / 先頭{len(rows)}行取得")
            # columns[] の measure 式も実際に通るか確かめる
            for c in ds.get("columns", []):
                st2, out2 = run(f"SELECT {c['expression']} AS v FROM ({sql.rstrip()}) x")
                if st2 != "OK":
                    print(f"      ✗ measure 「{c['displayName']}」 {st2}: {out2}")
                    bad += 1
        # ウィジェットの fieldName が実在するかを照合
        for pg in d["pages"]:
            for item in pg["layout"]:
                w = item["widget"]
                for q in w.get("queries", []):
                    dsn = q["query"]["datasetName"]
                    names = {fl["name"] for fl in q["query"]["fields"]}
                    enc = w.get("spec", {}).get("encodings", {})
                    refs = set()

                    def collect(node):
                        if isinstance(node, dict):
                            if "fieldName" in node:
                                refs.add(node["fieldName"])
                            for v in node.values():
                                collect(v)
                        elif isinstance(node, list):
                            for v in node:
                                collect(v)
                    collect(enc)
                    missing = refs - names
                    if missing:
                        print(f"      ✗ {w['name']}: encodings が query.fields に無い名前を参照 {missing}")
                        bad += 1
                    # 生の列参照はデータセットの列に実在すること
                    for fl in q["query"]["fields"]:
                        m = re.fullmatch(r"`(\w+)`", fl["expression"])
                        if m and dsn in ds_cols and m.group(1) not in ds_cols[dsn]:
                            print(f"      ✗ {w['name']}: 列 {m.group(1)} が {dsn} に無い")
                            bad += 1
    print(f"\n問題 {bad} 件")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["11_dashboards/sales.json"]))
