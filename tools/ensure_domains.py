#!/usr/bin/env python3
"""ドメイン4本が無ければ作り直す。消されても勝手に戻るようにするための本体。

ジョブとして1時間ごとに回す（tools/deploy_domain_guard.sh が仕掛ける）。
アカウントのドメイン上限が埋まっているため、枠を空ける一括削除が日常的に起きる。
2026-10-27 09:40 JST に我々の親ドメインが他のFEに消された（監査ログで確定）。
人が気づいて直すのでは間に合わないので、無ければ作る処理を定期実行する。

やること（冪等）
  1. 4本のうち無いものを作る（--draft は付けない）
  2. owner / subtitle を入れ直す（「使用中・期限」が掃除を止める唯一の手がかり）
  3. 作り直したときだけ標準出力に書く。変化が無ければ静かに終わる

ドメインを作り直しても**中にあった Page は戻らない**。
Page は `07_pages/pages_content.md` から再投入する（約30分）。
このスクリプトが効くのは「置き場所が消えて Page を作れない」状態の解消まで。
"""
from __future__ import annotations

import json
import subprocess
import sys

PROFILE = "fe-vm-serverless-rongzi-cpg-general"
PARENT = "Brickshouse Food and Beverage"
NOTE = "【使用中・2026-11-15まで / owner: rongzi.yan@databricks.com】"

# tag_key -> (表示名, subtitle, 親かどうか)
SPEC = [
    (PARENT, "Brickshouse Food and Beverage",
     "Brickshouse Food and Beverage 全社。売上・投下額・通貨の正本を置く", True),
    (f"{PARENT}/営業", "営業",
     "営業・販促の用語。受注・着地見込み・販促費", False),
    (f"{PARENT}/財務", "財務",
     "財務・経理の用語。純売上・売掛・買掛・原価率", False),
    (f"{PARENT}/マーケティング", "マーケティング",
     "マーケティングの用語。投下額・市場シェア・ROI（USD建て）", False),
]


def cli(*args: str, profile: bool = True) -> dict:
    cmd = ["databricks", *args]
    if profile and PROFILE:
        cmd += ["--profile", PROFILE]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:400])
    return json.loads(r.stdout) if r.stdout.strip() else {}


def listing() -> dict:
    out = cli("domains", "list-domains", "-o", "json")
    items = out if isinstance(out, list) else (out.get("domains") or [])
    return {d.get("tag_key"): d for d in items}


def main() -> int:
    me = str(cli("current-user", "me", "-o", "json")["id"])
    have = listing()
    created = []

    parent_id = (have.get(PARENT) or {}).get("domain_id")
    for key, name, sub, is_parent in SPEC:
        if key in have:
            continue
        args = ["domains", "create-domain", key, "--name", name,
                "--subtitle", f"{NOTE} {sub}"[:280]]
        if not is_parent:
            if not parent_id:
                print(f"!! 親が無いので {key} を作れない。次回の実行で解消する")
                continue
            args += ["--parent-domain-id", parent_id]
        d = cli(*args, "-o", "json")
        created.append(key)
        if is_parent:
            parent_id = d["domain_id"]
        have[key] = d

    # owner と subtitle は毎回入れ直す（更新されても戻す）
    for key, _name, sub, _p in SPEC:
        d = have.get(key)
        if not d:
            continue
        body = {"tag_key": key, "business_owner_ids": [me],
                "technical_owner_ids": [me],
                "subtitle": f"{NOTE} {sub}"[:280]}
        cli("domains", "update-domain", d["name"],
            "business_owner_ids,technical_owner_ids,subtitle",
            "--json", json.dumps(body, ensure_ascii=False), "-o", "json")

    if created:
        print("!! ドメインが消えていたので作り直した:")
        for k in created:
            print(f"   {k}  ({have[k]['domain_id']})")
        print("   Page は戻らない。07_pages/pages_content.md から再投入が必要。")
    else:
        print("ドメイン4本すべて健在。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
