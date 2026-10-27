#!/usr/bin/env python3
"""
ECM の列コメントが宣言している値域と、silver の実データが食い違っていないか調べる。

business.py で列を業務的に上書きすると、ECM のコメントに書かれた値域（`Valid values are a|b|c`）
と実データがずれる。ずれていると Genie がコメントを信じて WHERE 句を間違えるため、
正しい質問に答えられなくなる（実際に channel で起きた）。
上書きするなら、コメント側も上書きしなければならない。
"""
import json, re, subprocess, sys, time
from pathlib import Path

PROFILE = "fe-vm-serverless-rongzi-cpg-general"
WAREHOUSE = "2e13820648d1b0bf"
CATALOG = "rongzi_catalog_dev"
BASE = Path(__file__).resolve().parent.parent
ENUM = re.compile(r"^[A-Za-z0-9_|\-\. ]+$")


def api(method, path, payload=None):
    cmd = ["databricks", "api", method, path, "--profile", PROFILE]
    if payload is not None:
        cmd += ["--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {"_err": (r.stderr or r.stdout).strip()[:300]}
    return json.loads(r.stdout or "{}")


def run(stmt):
    res = api("post", "/api/2.0/sql/statements", {
        "statement": stmt, "warehouse_id": WAREHOUSE, "catalog": CATALOG,
        "wait_timeout": "50s", "on_wait_timeout": "CONTINUE"})
    if "_err" in res:
        return None
    sid = res.get("statement_id")
    while (res.get("status") or {}).get("state") in ("PENDING", "RUNNING"):
        time.sleep(2)
        res = api("get", f"/api/2.0/sql/statements/{sid}")
    if (res.get("status") or {}).get("state") != "SUCCEEDED":
        return None
    return (res.get("result") or {}).get("data_array") or []


def main():
    schema = json.loads((BASE / "02_data" / "schema.json").read_text())
    targets = []
    for key, meta in schema.items():
        for c in meta["columns"]:
            v = c.get("values")
            if not v or not isinstance(v, list) or len(v) < 2:
                continue          # 正規表現や単値は対象外（列挙だけ見る）
            if any(str(x).startswith("^") for x in v):
                continue
            targets.append((key, c["name"], [str(x).strip() for x in v]))

    print(f"列挙値域を宣言している列: {len(targets)}")
    bad = []
    for key, col, allowed in targets:
        sch, tbl = key.split(".")
        rows = run(f"SELECT DISTINCT `{col}` FROM `{CATALOG}`.`{sch}`.`{tbl}` "
                   f"WHERE `{col}` IS NOT NULL LIMIT 50")
        if rows is None:
            continue
        actual = {r[0] for r in rows if r[0] not in (None, "")}
        if not actual:
            continue
        off = sorted(actual - set(allowed))
        if off:
            bad.append((key, col, allowed, off, sorted(actual)))

    print(f"\n宣言と実データが食い違う列: {len(bad)}\n")
    for key, col, allowed, off, actual in bad:
        print(f"  {key}.{col}")
        print(f"    宣言: {allowed}")
        print(f"    実際: {actual}")
        print(f"    宣言に無い値: {off}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
