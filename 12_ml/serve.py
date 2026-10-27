#!/usr/bin/env python3
"""衝突ランキングモデルの serving endpoint を立てる / 落とす。

デモ直前に立てて、終わったら落とす運用。scale-to-zero を有効にしているので
放置しても推論が来なければ課金は止まるが、落とし忘れを防ぐため delete も用意する。

  python3 12_ml/serve.py create
  python3 12_ml/serve.py status
  python3 12_ml/serve.py query          # 実際に1件推論して疎通を確認
  python3 12_ml/serve.py delete
"""
import json
import subprocess
import sys

# --profile を必ず渡す。この Mac の ~/.databrickscfg は [DEFAULT] が別のワークスペース
# （fevm-rongzi-serverless）を指しているため、省略すると**別のワークスペースに**
# endpoint が建つ。モデルは同じメタストアにあるので動いてしまい、気づきにくい。
PROFILE = "fe-vm-serverless-rongzi-cpg-general"
ENDPOINT = "brickshouse-conflict-ranker"
MODEL = "rongzi_catalog_dev.semantics_ops.conflict_ranker"
VERSION = "3"


def cli(*args: str, body: dict | None = None) -> dict:
    cmd = ["databricks", *args, "--profile", PROFILE]
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:600])
    return json.loads(r.stdout) if r.stdout.strip() else {}


def create() -> None:
    body = {
        "name": ENDPOINT,
        "config": {
            "served_entities": [{
                "name": "conflict-ranker-1",
                "entity_name": MODEL,
                "entity_version": VERSION,
                "workload_size": "Small",
                "scale_to_zero_enabled": True,
            }],
        },
    }
    # --no-wait を付けないと CLI が READY まで待ち、20分でタイムアウトして
    # 「timed out: current status: IN_PROGRESS」と出る。作成自体は進んでいるので
    # 待たずに返し、status でポーリングする。
    out = cli("serving-endpoints", "create", "--no-wait", body=body)
    print(f"created {out.get('name')} state={json.dumps(out.get('state', {}), ensure_ascii=False)}")
    print("コンテナの作成に10〜20分かかる。status で確認する。")


def update() -> None:
    """既存 endpoint の served entity を VERSION に差し替える。
    作成に失敗した状態（UPDATE_FAILED）からの建て直しもこれで足りる。"""
    body = {"served_entities": [{
        "name": f"conflict-ranker-{VERSION}",
        "entity_name": MODEL,
        "entity_version": VERSION,
        "workload_size": "Small",
        "scale_to_zero_enabled": True,
    }]}
    cli("serving-endpoints", "update-config", ENDPOINT, "--no-wait", body=body)
    print(f"{ENDPOINT} -> v{VERSION} に差し替え中。status で確認する。")


def status() -> None:
    out = cli("serving-endpoints", "get", ENDPOINT)
    st = out.get("state", {})
    print(f"{ENDPOINT}  ready={st.get('ready')}  update={st.get('config_update')}")
    for e in out.get("config", {}).get("served_entities", []):
        print(f"  {e.get('entity_name')} v{e.get('entity_version')} "
              f"scale_to_zero={e.get('scale_to_zero_enabled')}")


# 学習時の列順と完全に一致させる必要がある（train_conflict_ranker.py の FEATURES）。
# 列が足りない・順序が違うと serving が "Failed to enforce schema" で拒否する。
FEATURES = ["n_objects", "n_departments", "n_schemas", "log_max_over_min",
            "cross_layer", "n_currencies", "currency_mixed", "in_metric_view",
            "certified_count", "name_has_amount", "name_has_rate",
            "name_has_count", "name_has_usd", "comment_jaccard_avg",
            "comment_missing"]
WAREHOUSE = "2e13820648d1b0bf"
CATALOG = "rongzi_catalog_dev"


def query() -> None:
    """特徴量テーブルから3件引いて推論させ、疎通とスコアの妥当さを見る。"""
    stmt = f"""
        SELECT measure_name, n_objects, n_departments, n_schemas,
               log10(greatest(max_over_min, 1.0)) AS log_max_over_min,
               cross_layer, n_currencies, currency_mixed, in_metric_view,
               certified_count, name_has_amount, name_has_rate,
               name_has_count, name_has_usd,
               coalesce(comment_jaccard_avg, 0.0) AS comment_jaccard_avg,
               CASE WHEN comment_jaccard_avg IS NULL THEN 1 ELSE 0 END AS comment_missing
        FROM {CATALOG}.semantics_ops.conflict_feature
        WHERE measure_name IN ('total_net_amount', 'dollar_sales', 'avg_roi_index')
        ORDER BY measure_name"""
    res = cli("api", "post", "/api/2.0/sql/statements",
              body={"statement": stmt, "warehouse_id": WAREHOUSE,
                    "wait_timeout": "30s"})
    cols = [c["name"] for c in res["manifest"]["schema"]["columns"]]
    rows = res["result"]["data_array"]
    recs, names = [], []
    for row in rows:
        d = dict(zip(cols, row))
        names.append(d["measure_name"])
        recs.append({k: float(d[k]) for k in FEATURES})
    out = cli("serving-endpoints", "query", ENDPOINT,
              body={"dataframe_records": recs})
    for name, score in zip(names, out["predictions"]):
        print(f"  {name:20s} 衝突スコア {score:.4f}")


def delete() -> None:
    cli("serving-endpoints", "delete", ENDPOINT)
    print(f"deleted {ENDPOINT}")


if __name__ == "__main__":
    {"create": create, "update": update, "status": status,
     "query": query, "delete": delete}[
        sys.argv[1] if len(sys.argv) > 1 else "status"]()
