#!/usr/bin/env python3
"""デモ直前に流す点検。ドメイン4本とタグが生きているかを確認する。

なぜ必要か
  2026-10-27 09:40 JST、他のFEがアカウントのドメインを17件まとめて削除し、
  その中に我々の親ドメインが入っていた（監査ログで確認）。
  このアカウントはドメイン上限 1000 に張り付いているため、
  枠を空けるための掃除が繰り返し起きる。**また消される前提で点検する。**

  tag policy は消えない（上の件でも4本すべて残っていた）。消えるのは domain だけ。
  domain が消えると Discover のドメイン画面と Page の置き場所が消える。
"""
from __future__ import annotations

import json
import subprocess
import sys

PROFILE = "fe-vm-serverless-rongzi-cpg-general"
WAREHOUSE = "2e13820648d1b0bf"
CATALOG = "rongzi_catalog_dev"
PARENT = "Brickshouse Food and Beverage"
WANT = [PARENT, f"{PARENT}/営業", f"{PARENT}/財務", f"{PARENT}/マーケティング"]


def cli(*args: str) -> dict:
    r = subprocess.run(["databricks", *args, "--profile", PROFILE],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:400])
    return json.loads(r.stdout) if r.stdout.strip() else {}


def main() -> int:
    bad = 0

    out = cli("domains", "list-domains", "-o", "json")
    items = out if isinstance(out, list) else (out.get("domains") or [])
    have = {d.get("tag_key"): d for d in items}
    print(f"ドメイン（アカウント全体 {len(items)} 件）")
    for key in WANT:
        d = have.get(key)
        if d is None:
            print(f"  ✗ 無い   {key}  ← 作り直しが必要（--draft は付けない）")
            bad += 1
        elif d.get("effective_draft"):
            print(f"  △ draft  {key}  ← 掃除の対象になりやすい")
            bad += 1
        else:
            print(f"  ✓        {key}  {d['domain_id']}")

    res = cli("api", "post", "/api/2.0/sql/statements", "--json", json.dumps({
        "statement": f"""
            SELECT tag_name, count(*) AS n
            FROM {CATALOG}.information_schema.table_tags
            WHERE tag_name LIKE '{PARENT}%'
               OR tag_name = 'system.certification_status'
            GROUP BY 1 ORDER BY 1""",
        "warehouse_id": WAREHOUSE, "wait_timeout": "50s"}))
    rows = res.get("result", {}).get("data_array") or []
    print("\nUC のタグ")
    if not rows:
        print("  ✗ 0件 ← パイプラインを回した後は落ちる。"
              "04_asset_domain_tags.py と 03_governance_on.sql を流し直す")
        bad += 1
    for name, n in rows:
        print(f"  ✓ {name:46s} {int(n):3d} 件")

    print("\n" + ("すべて問題なし" if bad == 0 else f"要対応 {bad} 件"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
