#!/usr/bin/env python3
"""ドメインを「掃除されにくい」状態にする。

アカウントはドメイン上限 1000 に張り付いていて、枠を空けるための一括削除が
日常的に起きる（直近5日で16人が100件。うち1件が我々の親ドメインだった）。
削除を防ぐ仕組みは無いので、**掃除する人に「これは使用中」と見える**ようにする。

効くと考えられるもの（989件中の分布を見て判断した）
  - owner が設定されている         … 464/989 件だけ。無いと「持ち主不明」に見える
  - draft でない                   … draft は捨てても良さそうに見える
  - 配下にアセットがある           … 0件のドメインは掃除の第一候補
  - subtitle に用途と期限が書いてある … 人が読んで止まる唯一の手がかり

消されたときの復旧は `tools/check_domains.py` で検知 → `create-domain` 4回（約1分）。
tag policy は消えないので、鍵は残っている。
"""
from __future__ import annotations

import json
import subprocess
import sys

PROFILE = "fe-vm-serverless-rongzi-cpg-general"
PARENT = "Brickshouse Food and Beverage"
NOTE = "【使用中・2026-11-15まで / owner: rongzi.yan@databricks.com】"

SUBTITLES = {
    PARENT: "Brickshouse Food and Beverage 全社。売上・投下額・通貨の正本を置く",
    f"{PARENT}/営業": "営業・販促の用語。受注・着地見込み・販促費",
    f"{PARENT}/財務": "財務・経理の用語。純売上・売掛・買掛・原価率",
    f"{PARENT}/マーケティング": "マーケティングの用語。投下額・市場シェア・ROI（USD建て）",
}


def cli(*args: str) -> dict:
    r = subprocess.run(["databricks", *args, "--profile", PROFILE],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:400])
    return json.loads(r.stdout) if r.stdout.strip() else {}


def main() -> int:
    me = cli("current-user", "me", "-o", "json")["id"]
    out = cli("domains", "list-domains", "-o", "json")
    items = out if isinstance(out, list) else (out.get("domains") or [])
    have = {d.get("tag_key"): d for d in items}

    missing = [k for k in SUBTITLES if k not in have]
    if missing:
        print("先にドメインを作ってください（check_domains.py 参照）:")
        for k in missing:
            print(f"  ✗ {k}")
        return 1

    for key, sub in SUBTITLES.items():
        d = have[key]
        body = {"tag_key": key,
                "business_owner_ids": [str(me)],
                "technical_owner_ids": [str(me)],
                "subtitle": f"{NOTE} {sub}"[:280]}
        cli("domains", "update-domain", d["name"],
            "business_owner_ids,technical_owner_ids,subtitle",
            "--json", json.dumps(body, ensure_ascii=False), "-o", "json")
        print(f"  ✓ {key}")

    owned = sum(1 for d in items
                if (d.get("business_owner_ids") or d.get("technical_owner_ids")))
    print(f"\nowner が設定されたドメイン: {owned} → {owned + len(SUBTITLES)} / {len(items)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
