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

ENDPOINT = "brickshouse-conflict-ranker"
MODEL = "rongzi_catalog_dev.semantics_ops.conflict_ranker"
VERSION = "3"


def cli(*args: str, body: dict | None = None) -> dict:
    cmd = ["databricks", *args]
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


def query() -> None:
    """features.json の先頭1件を投げて疎通を見る。"""
    feats = json.loads(open("12_ml/features.json", encoding="utf-8").read())
    rows = feats if isinstance(feats, list) else feats.get("rows", [])
    cols = [c for c in rows[0] if isinstance(rows[0][c], (int, float))]
    rec = {c: rows[0][c] for c in cols}
    body = {"dataframe_records": [rec]}
    out = cli("serving-endpoints", "query", ENDPOINT, body=body)
    print(f"入力: {json.dumps(rec, ensure_ascii=False)}")
    print(f"出力: {json.dumps(out.get('predictions'), ensure_ascii=False)}")


def delete() -> None:
    cli("serving-endpoints", "delete", ENDPOINT)
    print(f"deleted {ENDPOINT}")


if __name__ == "__main__":
    {"create": create, "update": update, "status": status,
     "query": query, "delete": delete}[
        sys.argv[1] if len(sys.argv) > 1 else "status"]()
