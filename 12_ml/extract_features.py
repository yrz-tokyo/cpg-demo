#!/usr/bin/env python3
"""
同名の数値列グループを全部洗い出し、ML の特徴量を作る。

検出器（10_detect）は metric view の measure だけを見ていた。こちらは
silver 30本とマート13本の数値列をすべて見るので母数が一桁増える（82グループ / 201列）。
これが「レビュー待ちの行列」で、ML の役目は**行列の並べ替え**。
スチュワードが上から見るだけで本物の衝突に当たるようにする。

特徴量は**メタデータとデータから取れるものだけ**にする:
  n_objects        同名の列を持つオブジェクト数
  n_departments    関与する部門数（スキーマのタグから）
  n_schemas        関与するスキーマ数
  max_over_min     その列で集計した値の最大/最小比
  cross_layer      core と mart の両方に跨るか（マートは core の集計なので同義のことが多い）
  currency_mixed   関与する表の建値が混ざるか
  name_* 　        列名のトークン（amount / rate / count / pct / usd ...）
  comment_jaccard  列コメントの語の重なり（低いほど別概念）
  certified_count  認定済みオブジェクトの数
  in_metric_view   metric view の measure として露出しているか（業務が実際に触る面）

ラベルはここでは付けない。人の判断（Lakebase の decision）が正。
出力: 12_ml/features.json と semantics_ops.conflict_feature
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from itertools import combinations
from pathlib import Path

PROFILE = "fe-vm-serverless-rongzi-cpg-general"
WAREHOUSE = "2e13820648d1b0bf"
CATALOG = "rongzi_catalog_dev"
OUT = Path(__file__).resolve().parent

CORE = ["master_core", "sales_core", "finance_core", "trade_core", "marketing_core", "procure_core"]
MART = ["master_mart", "sales_mart", "finance_mart", "trade_mart",
        "marketing_mart", "procure_mart", "xdept_mart"]
NUMERIC = ("DOUBLE", "DECIMAL", "LONG", "INT", "FLOAT", "BIGINT")
STOP = set("the of a an and or to for in on by with is are this that it its as at from "
           "数 の に は が を と で や へ".split())


def api(method, path, payload=None):
    cmd = ["databricks", "api", method, path, "--profile", PROFILE]
    if payload is not None:
        cmd += ["--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:400])
    return json.loads(r.stdout or "{}")


def sql(stmt, timeout_s=180):
    res = api("post", "/api/2.0/sql/statements", {
        "statement": stmt, "warehouse_id": WAREHOUSE, "catalog": CATALOG,
        "wait_timeout": "30s", "on_wait_timeout": "CONTINUE"})
    sid = res.get("statement_id")
    deadline = time.time() + timeout_s
    while (res.get("status") or {}).get("state") in ("PENDING", "RUNNING"):
        if time.time() > deadline:
            raise TimeoutError(stmt[:90])
        time.sleep(1.2)
        res = api("get", f"/api/2.0/sql/statements/{sid}")
    st = (res.get("status") or {}).get("state")
    if st != "SUCCEEDED":
        raise RuntimeError(f"{st}: {json.dumps((res.get('status') or {}).get('error'), ensure_ascii=False)[:280]}")
    cols = [c["name"] for c in ((res.get("manifest") or {}).get("schema") or {}).get("columns", [])]
    rows = (res.get("result") or {}).get("data_array") or []
    return [dict(zip(cols, r)) for r in rows]


def tokens(text):
    if not text:
        return set()
    t = re.sub(r"[^\w\s]", " ", text.lower())
    return {w for w in t.split() if len(w) > 2 and w not in STOP}


def jaccard(a, b):
    if not a or not b:
        return None
    return round(len(a & b) / len(a | b), 4)


def main():
    schemas = "', '".join(CORE + MART)
    types = "', '".join(NUMERIC)
    print("1) 数値列とメタデータを集める")
    cols = sql(f"""
        SELECT c.table_schema, c.table_name, c.column_name, c.data_type, c.comment,
               t.table_type, st.tag_value AS department, tt.tag_value AS certification
        FROM {CATALOG}.information_schema.columns c
        JOIN {CATALOG}.information_schema.tables t
          ON t.table_schema = c.table_schema AND t.table_name = c.table_name
        LEFT JOIN (SELECT schema_name, max(tag_value) tag_value
                   FROM {CATALOG}.information_schema.schema_tags
                   WHERE tag_name LIKE 'Brickshouse Food and Beverage/%' GROUP BY 1) st
          ON st.schema_name = c.table_schema
        LEFT JOIN (SELECT schema_name, table_name, max(tag_value) tag_value
                   FROM {CATALOG}.information_schema.table_tags
                   WHERE tag_name = 'system.certification_status' GROUP BY 1,2) tt
          ON tt.schema_name = c.table_schema AND tt.table_name = c.table_name
        WHERE c.table_schema IN ('{schemas}')
          AND t.table_type <> 'MANAGED'
          AND c.data_type IN ('{types}')
          AND c.column_name NOT LIKE '%_id' AND c.column_name NOT LIKE '%_code'
    """)
    print(f"   数値列 {len(cols)} 件")

    groups = {}
    for c in cols:
        groups.setdefault(c["column_name"], []).append(c)
    shared = {k: v for k, v in groups.items()
              if len({(x["table_schema"], x["table_name"]) for x in v}) > 1}
    print(f"   同名グループ {len(shared)} / 関与する列 {sum(len(v) for v in shared.values())}")

    print("2) 各列の実測値を取る（集計できない列はグループから落とす）")
    for name, members in sorted(shared.items()):
        for m in members:
            fq = f"`{CATALOG}`.`{m['table_schema']}`.`{m['table_name']}`"
            try:
                if m["table_type"] == "METRIC_VIEW":
                    r = sql(f"SELECT MEASURE(`{name}`) AS v FROM {fq}")
                else:
                    r = sql(f"SELECT SUM(`{name}`) AS v FROM {fq}")
                m["observed"] = float(r[0]["v"]) if r and r[0]["v"] is not None else None
            except Exception:
                m["observed"] = None

    print("3) 建値を調べる（currency_code を持つ表だけ）")
    ccy = {}
    for r in sql(f"""
        SELECT table_schema, table_name, column_name
        FROM {CATALOG}.information_schema.columns
        WHERE table_schema IN ('{schemas}')
          AND column_name IN ('currency_code', 'spend_currency_code', 'budget_currency_code')
    """):
        key = (r["table_schema"], r["table_name"])
        try:
            vals = sql(f"SELECT DISTINCT `{r['column_name']}` AS v "
                       f"FROM `{CATALOG}`.`{r['table_schema']}`.`{r['table_name']}` "
                       f"WHERE `{r['column_name']}` IS NOT NULL LIMIT 5")
            ccy.setdefault(key, set()).update(x["v"] for x in vals if x["v"])
        except Exception:
            pass

    print("4) 特徴量を組み立てる")
    feats = []
    for name, members in sorted(shared.items()):
        live = [m for m in members if m.get("observed") is not None]
        if len(live) < 2:
            continue
        vals = [abs(m["observed"]) for m in live if m["observed"] != 0] or [1.0]
        depts = {m.get("department") for m in live if m.get("department")}
        schs = {m["table_schema"] for m in live}
        objs = sorted(f"{m['table_schema']}.{m['table_name']}" for m in live)
        currencies = set()
        for m in live:
            currencies |= ccy.get((m["table_schema"], m["table_name"]), set())
        if name.endswith("_usd"):
            currencies.add("USD")
        cmts = [tokens(m.get("comment")) for m in live]
        pairs = [jaccard(a, b) for a, b in combinations(cmts, 2)]
        pairs = [p for p in pairs if p is not None]
        feats.append({
            "measure_name": name,
            "objects": objs,
            "n_objects": len(live),
            "n_departments": len(depts),
            "n_schemas": len(schs),
            "departments": sorted(depts),
            "max_over_min": round(max(vals) / max(min(vals), 1e-9), 4),
            "cross_layer": int(bool({s for s in schs if s in CORE})
                               and bool({s for s in schs if s in MART})),
            "n_currencies": len(currencies),
            "currency_mixed": int(len(currencies) > 1),
            "in_metric_view": int(any(m["table_type"] == "METRIC_VIEW" for m in live)),
            "certified_count": sum(1 for m in live if m.get("certification") == "certified"),
            "name_has_amount": int(bool(re.search(r"amount|spend|sales|cost|price|revenue", name))),
            "name_has_rate": int(bool(re.search(r"rate|pct|ratio|index", name))),
            "name_has_count": int(bool(re.search(r"count|qty|quantity|units", name))),
            "name_has_usd": int(name.endswith("_usd")),
            "comment_jaccard_min": round(min(pairs), 4) if pairs else None,
            "comment_jaccard_avg": round(sum(pairs) / len(pairs), 4) if pairs else None,
            "observed": {f"{m['table_schema']}.{m['table_name']}": m["observed"] for m in live},
        })

    feats.sort(key=lambda x: (-x["n_objects"], -x["max_over_min"]))
    (OUT / "features.json").write_text(json.dumps(feats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n特徴量 {len(feats)} グループ -> 12_ml/features.json")
    print(f"{'measure':34s} obj dept 最大/最小   跨層 通貨 MV 認定 コメント類似")
    for f in feats[:22]:
        print(f"  {f['measure_name']:32s} {f['n_objects']:3d} {f['n_departments']:4d} "
              f"{f['max_over_min']:10,.1f} {f['cross_layer']:4d} {f['n_currencies']:4d} "
              f"{f['in_metric_view']:2d} {f['certified_count']:4d} "
              f"{(f['comment_jaccard_avg'] if f['comment_jaccard_avg'] is not None else -1):8.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
