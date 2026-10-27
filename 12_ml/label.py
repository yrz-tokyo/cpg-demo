#!/usr/bin/env python3
"""
特徴量に人の判断（ラベル）を付け、UC の semantics_ops に書き出す。

方針は 12_ml/LABELING_POLICY.md。要点だけ:
  label=1  業務の言葉が同じになり、かつ意味が違う（どちらを使うかで答えが変わる）
  label=0  同じ列の core→mart 集計 / 業務の言葉にならない技術列 / 単位も universe も同じ

ラベルは**私（構築者）がスチュワード役として**付けたもの。合成データなので実在の
スチュワードは存在しない。したがってモデルが主張できるのは
「保留したスチュワード判断を再現できる」までで、「衝突を発見した」ではない。

1グループずつ、列コメントと実測値を見て付ける。
機械的に一括適用した箇所は rationale に「方針Xの一括適用」と書く。

使い方
  python3 12_ml/label.py --review      # 未ラベルのグループを人が読む形で出す
  python3 12_ml/label.py --apply       # labels.json を UC に書き出す
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
SCHEMA = "semantics_ops"
HERE = Path(__file__).resolve().parent


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


def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def review():
    feats = json.loads((HERE / "features.json").read_text(encoding="utf-8"))
    labels = {}
    p = HERE / "labels.json"
    if p.exists():
        labels = {x["measure_name"]: x for x in json.loads(p.read_text(encoding="utf-8"))}
    todo = [f for f in feats if f["measure_name"] not in labels]
    print(f"全 {len(feats)} グループ / ラベル済み {len(labels)} / 未ラベル {len(todo)}\n")
    for f in todo:
        j = f["comment_jaccard_avg"]
        print(f"■ {f['measure_name']}")
        print(f"   オブジェクト {f['n_objects']}  部門 {f['n_departments']}{f['departments']}  "
              f"最大/最小 {f['max_over_min']:,.1f}  跨層 {f['cross_layer']}  "
              f"建値 {f['n_currencies']}  MV {f['in_metric_view']}  "
              f"コメント類似 {j if j is not None else '-'}")
        for o, v in sorted(f["observed"].items(), key=lambda kv: -abs(kv[1] or 0)):
            print(f"     {o:46s} {v:>22,.2f}")
        print()


def apply_labels():
    feats = {f["measure_name"]: f for f in
             json.loads((HERE / "features.json").read_text(encoding="utf-8"))}
    labels = json.loads((HERE / "labels.json").read_text(encoding="utf-8"))
    print(f"特徴量 {len(feats)} / ラベル {len(labels)}")

    sql(f"""CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.conflict_feature (
      measure_name STRING NOT NULL COMMENT '同名になっている数値列の名前',
      objects STRING COMMENT '関与するオブジェクト（schema.table をカンマ区切り）',
      n_objects INT, n_departments INT, n_schemas INT,
      max_over_min DOUBLE COMMENT 'その列で集計した値の最大/最小比',
      cross_layer INT COMMENT 'core と mart の両方に跨るか（跨るなら同じ列の集計である可能性が高い）',
      n_currencies INT, currency_mixed INT, in_metric_view INT, certified_count INT,
      name_has_amount INT, name_has_rate INT, name_has_count INT, name_has_usd INT,
      comment_jaccard_avg DOUBLE COMMENT '列コメントの語の重なり（低いほど別概念）',
      observed STRING COMMENT 'オブジェクトごとの実測値（JSON）',
      extracted_at TIMESTAMP)
      COMMENT '定義衝突ランキングモデルの特徴量。12_ml/extract_features.py が作る。メタデータとデータだけから取れるものに限る。'""")
    sql(f"""CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.conflict_label (
      measure_name STRING NOT NULL,
      label INT NOT NULL COMMENT '1=本物の衝突（正本を決める必要がある） 0=衝突ではない',
      rationale STRING NOT NULL COMMENT 'なぜそう判断したか。方針は 12_ml/LABELING_POLICY.md',
      labeled_by STRING NOT NULL COMMENT '判断した人。合成データなので構築者がスチュワード役',
      labeled_at TIMESTAMP)
      COMMENT '定義衝突の人による判断。モデルの学習ラベル。構築者がスチュワード役として付けたものであり、実在の業務担当者の合議ではない。'""")

    sql(f"DELETE FROM {CATALOG}.{SCHEMA}.conflict_feature WHERE true")
    sql(f"DELETE FROM {CATALOG}.{SCHEMA}.conflict_label WHERE true")

    vals = []
    for name, f in feats.items():
        vals.append("(" + ", ".join([
            q(name), q(",".join(f["objects"])), str(f["n_objects"]),
            str(f["n_departments"]), str(f["n_schemas"]), repr(float(f["max_over_min"])),
            str(f["cross_layer"]), str(f["n_currencies"]), str(f["currency_mixed"]),
            str(f["in_metric_view"]), str(f["certified_count"]),
            str(f["name_has_amount"]), str(f["name_has_rate"]),
            str(f["name_has_count"]), str(f["name_has_usd"]),
            "NULL" if f["comment_jaccard_avg"] is None else repr(float(f["comment_jaccard_avg"])),
            q(json.dumps(f["observed"], ensure_ascii=False)), "current_timestamp()"]) + ")")
    print(f"   特徴量 {len(vals)} 行を投入")
    for i in range(0, len(vals), 8):
        sql(f"INSERT INTO {CATALOG}.{SCHEMA}.conflict_feature VALUES " + ", ".join(vals[i:i+8]))

    lv = ["(" + ", ".join([q(x["measure_name"]), str(int(x["label"])), q(x["rationale"]),
                           q(x.get("labeled_by", "rongzi.yan@databricks.com (builder as steward)")),
                           "current_timestamp()"]) + ")" for x in labels]
    print(f"   ラベル {len(lv)} 行を投入")
    for i in range(0, len(lv), 8):
        sql(f"INSERT INTO {CATALOG}.{SCHEMA}.conflict_label VALUES " + ", ".join(lv[i:i+8]))

    chk = sql(f"""SELECT l.label, count(*) n FROM {CATALOG}.{SCHEMA}.conflict_label l
                  JOIN {CATALOG}.{SCHEMA}.conflict_feature f USING (measure_name)
                  GROUP BY 1 ORDER BY 1""")
    print("UC に書き出しました:")
    for r in chk:
        print(f"   label={r['label']}  {r['n']} 件")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.apply:
        sys.exit(apply_labels())
    sys.exit(review())
