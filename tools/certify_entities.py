#!/usr/bin/env python3
"""ダッシュボード / Genie Agent / App に「認定」と所属ドメインのタグを付ける。

UC のテーブル・ビュー・metric view は SQL の `ALTER ... SET TAGS` で付けられるが
（`05_governance/03_governance_on.sql` と `04_asset_domain_tags.py`）、
ワークスペース側の資産（dashboards / geniespaces / apps / notebooks）は
別 API（workspace-entity-tag-assignments）になる。

実機で分かったこと:
- CLI のヘルプは tag_key に `.` を使えないと書いてあるが、
  `system.certification_status` は**通る**。ヘルプの記述が実態と合っていない
- 既に同じキーが付いていると `already exists` で失敗する。更新は update を使う
- --profile を省くと別ワークスペースに向く（~/.databrickscfg の [DEFAULT] が別物）
"""
from __future__ import annotations

import json
import subprocess

PROFILE = "fe-vm-serverless-rongzi-cpg-general"
PARENT = "Brickshouse Food and Beverage"
CERT = "system.certification_status"

# (entity_type, entity_id, 表示名, 親ドメインの値)
TARGETS = [
    ("dashboards", "01f1d1385cd91982aa70e86ddc46ded9", "Brickshouse 営業（販促を含む）", "sales"),
    ("dashboards", "01f1d1385d9c194ea7b12f177f6dd81a", "Brickshouse 財務", "finance"),
    ("dashboards", "01f1d1385e72118dbde6b3f62aa9859f", "Brickshouse マーケティング", "marketing"),
    ("geniespaces", "01f1d10db91f1a0f8058c509f70f077a", "Agent 営業", "sales"),
    ("geniespaces", "01f1d10dba011b8981645be70f048880", "Agent 財務", "finance"),
    ("geniespaces", "01f1d10dbaf61f16b0d3ef3eff342016", "Agent マーケティング", "marketing"),
    ("geniespaces", "01f1d10dbbd51e24985da13d0ba87c5a", "Agent 全社横断", "cross-department"),
    ("apps", "cpg-cockpit", "App データ統治コックピット", "cross-department"),
]


def assign(etype: str, eid: str, key: str, value: str) -> str:
    """付いていなければ create、付いていれば update。"""
    for verb in ("create-tag-assignment", "update-tag-assignment"):
        args = [etype, eid, key]
        # update だけ UPDATE_MASK を4つめの位置引数で要求する
        if verb.startswith("update"):
            args.append("tag_value")
        cmd = ["databricks", "workspace-entity-tag-assignments", verb,
               *args, "--tag-value", value, "--profile", PROFILE]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return "OK" if verb.startswith("create") else "更新"
        if "already exists" not in (r.stderr + r.stdout):
            return (r.stderr or r.stdout).strip()[:120]
    return "失敗"


def main() -> None:
    ok = 0
    for etype, eid, label, dom in TARGETS:
        c = assign(etype, eid, CERT, "certified")
        d = assign(etype, eid, PARENT, dom)
        ok += (c in ("OK", "更新")) and (d in ("OK", "更新"))
        print(f"  {etype:12s} {label:30s} 認定={c:4s} ドメイン={d}")
    print(f"\n==== {ok} / {len(TARGETS)} ====")


if __name__ == "__main__":
    main()
