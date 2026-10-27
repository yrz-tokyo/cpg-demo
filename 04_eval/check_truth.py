#!/usr/bin/env python3
"""
question_bank.json の truth_sql 49本を全部流して、壊れていないかを先に確かめる。
壊れた truth_sql は「Genie が外した」と区別がつかないまま採点に混ざるので、
評価を回す前に必ずここを通す。
"""
import json, subprocess, sys, time
from pathlib import Path

PROFILE = "fe-vm-serverless-rongzi-cpg-general"
WAREHOUSE = "2e13820648d1b0bf"
CATALOG = "rongzi_catalog_dev"
BASE = Path(__file__).resolve().parent


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
        return "CLI_ERROR", res["_err"], None
    sid = res.get("statement_id")
    while (res.get("status") or {}).get("state") in ("PENDING", "RUNNING"):
        time.sleep(3)
        res = api("get", f"/api/2.0/sql/statements/{sid}")
    st = (res.get("status") or {}).get("state")
    if st != "SUCCEEDED":
        return st, json.dumps((res.get("status") or {}).get("error"), ensure_ascii=False)[:300], None
    rows = (res.get("result") or {}).get("data_array") or []
    return "OK", "", rows


def main():
    qs = json.loads((BASE / "question_bank.json").read_text())["questions"]
    bad, empty = [], []
    for q in qs:
        st, err, rows = run(q["truth_sql"])
        n = len(rows) if rows is not None else 0
        flag = ""
        if st != "OK":
            bad.append((q["id"], err)); flag = "  <-- 失敗"
        elif n == 0:
            empty.append(q["id"]); flag = "  <-- 0行（質問が成立しない）"
        else:
            # 全列 NULL の1行だけ、も実質 0 行
            allnull = n == 1 and all(v is None for v in rows[0])
            if allnull:
                empty.append(q["id"]); flag = "  <-- 全列NULL"
        print(f"  {q['id']:9s} {q['dept']:4s} {st:10s} {n:4d}行{flag}")
    print(f"\n成功 {len(qs)-len(bad)} / 失敗 {len(bad)} / 空 {len(empty)}")
    for i, e in bad:
        print(f"  失敗 {i}: {e}")
    if empty:
        print(f"  空: {empty}")
    return 1 if (bad or empty) else 0


if __name__ == "__main__":
    sys.exit(main())
