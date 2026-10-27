#!/usr/bin/env python3
"""ドメイン番犬。1時間ごとに回して、消えていたら作り直す（ジョブ側で動く本体）。

ローカル用の tools/ensure_domains.py と同じことをするが、
こちらは Databricks のジョブとして動くので CLI が無い。SDK の素の API を叩く。
エンドポイントは `/api/2.0/domains`（CLI の --debug で確認した）。

なぜジョブにするか
  アカウントのドメイン上限が埋まっており、枠を空ける一括削除が日常的に起きる。
  2026-10-27 09:40 JST、他のFEが8分間に17件消し、その1件が我々の親ドメインだった。
  人が気づいて直すのでは間に合わない。無ければ作る処理を定期実行して、
  「消えている時間」を最大1時間に抑える。

  ドメインが戻っても**中にあった Page は戻らない**。Page は
  07_pages/pages_content.md から再投入する。このジョブが守るのは置き場所だけ。
"""
from __future__ import annotations

from databricks.sdk import WorkspaceClient

PARENT = "Brickshouse Food and Beverage"
NOTE = "【使用中・2026-11-15まで / owner: rongzi.yan@databricks.com】"
SPEC = [
    (PARENT, "Brickshouse Food and Beverage",
     "Brickshouse Food and Beverage 全社。売上・投下額・通貨の正本を置く", True),
    (f"{PARENT}/営業", "営業", "営業・販促の用語。受注・着地見込み・販促費", False),
    (f"{PARENT}/財務", "財務", "財務・経理の用語。純売上・売掛・買掛・原価率", False),
    (f"{PARENT}/マーケティング", "マーケティング",
     "マーケティングの用語。投下額・市場シェア・ROI（USD建て）", False),
]

w = WorkspaceClient()


def api(method: str, path: str, body: dict | None = None, query: dict | None = None):
    return w.api_client.do(method, path, body=body, query=query) or {}


def listing() -> dict:
    out = api("GET", "/api/2.0/domains", query={"page_size": 1000})
    return {d.get("tag_key"): d for d in (out.get("domains") or [])}


def main() -> None:
    me = str(w.current_user.me().id)
    have = listing()
    created = []
    parent_id = (have.get(PARENT) or {}).get("domain_id")

    for key, name, sub, is_parent in SPEC:
        if key in have:
            continue
        body = {"tag_key": key, "name": name, "subtitle": f"{NOTE} {sub}"[:280]}
        if not is_parent:
            if not parent_id:
                print(f"!! 親が無いので {key} は次回に回す")
                continue
            body["parent_domain_id"] = parent_id
        d = api("POST", "/api/2.0/domains", body={"domain": body})
        created.append(key)
        have[key] = d
        if is_parent:
            parent_id = d.get("domain_id")

    for key, _name, sub, _p in SPEC:
        d = have.get(key)
        if not d:
            continue
        api("PATCH", f"/api/2.0/{d['name']}",
            query={"update_mask": "business_owner_ids,technical_owner_ids,subtitle"},
            body={"tag_key": key, "business_owner_ids": [me],
                  "technical_owner_ids": [me],
                  "subtitle": f"{NOTE} {sub}"[:280]})

    if created:
        print("!! ドメインが消えていたので作り直した: " + " / ".join(created))
        print("   Page は戻らない。pages_content.md から再投入が必要。")
    else:
        print(f"ドメイン4本すべて健在（アカウント全体 {len(have)} 件を確認）")


main()
