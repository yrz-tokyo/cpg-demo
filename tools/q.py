#!/usr/bin/env python3
"""SQL を1本流して結果を表で出す（確認用）。usage: q.py "SELECT ..." または q.py -f file.sql"""
import json, subprocess, sys, time
PROFILE = "fe-vm-serverless-rongzi-cpg-general"
WAREHOUSE = "2e13820648d1b0bf"
CATALOG = "rongzi_catalog_dev"

def api(method, path, payload=None):
    cmd = ["databricks", "api", method, path, "--profile", PROFILE]
    if payload is not None:
        cmd += ["--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit((r.stderr or r.stdout).strip()[:800])
    return json.loads(r.stdout or "{}")

def run(stmt):
    res = api("post", "/api/2.0/sql/statements", {
        "statement": stmt, "warehouse_id": WAREHOUSE, "catalog": CATALOG,
        "wait_timeout": "50s", "on_wait_timeout": "CONTINUE"})
    sid = res.get("statement_id")
    while (res.get("status") or {}).get("state") in ("PENDING", "RUNNING"):
        time.sleep(3)
        res = api("get", f"/api/2.0/sql/statements/{sid}")
    st = (res.get("status") or {}).get("state")
    if st != "SUCCEEDED":
        raise SystemExit(f"{st}: {json.dumps((res.get('status') or {}).get('error'), ensure_ascii=False)[:600]}")
    man = res.get("manifest", {}).get("schema", {}).get("columns", [])
    cols = [c["name"] for c in man]
    rows = (res.get("result") or {}).get("data_array") or []
    w = [max(len(c), *(len(str(r[i])) if r[i] is not None else 4 for r in rows)) if rows else len(c)
         for i, c in enumerate(cols)]
    print(" | ".join(c.ljust(w[i]) for i, c in enumerate(cols)))
    print("-+-".join("-" * x for x in w))
    for r in rows:
        print(" | ".join((str(v) if v is not None else "NULL").ljust(w[i]) for i, v in enumerate(r)))
    print(f"({len(rows)} rows)")

if __name__ == "__main__":
    if sys.argv[1] == "-f":
        run(open(sys.argv[2], encoding="utf-8").read())
    else:
        run(sys.argv[1])
