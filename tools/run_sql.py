#!/usr/bin/env python3
"""SQL ファイルを文単位で Databricks SQL warehouse に流す（CLI の api コマンド経由）。"""
import json, re, subprocess, sys, time

PROFILE = "fe-vm-serverless-rongzi-cpg-general"
WAREHOUSE = "2e13820648d1b0bf"
CATALOG = "rongzi_catalog_dev"

def api(method, path, payload=None):
    cmd = ["databricks", "api", method, path, "--profile", PROFILE]
    if payload is not None:
        cmd += ["--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {"_cli_error": (r.stderr or r.stdout).strip()[:500]}
    try:
        return json.loads(r.stdout or "{}")
    except Exception:
        return {"_raw": r.stdout[:500]}

def split_statements(sql):
    """
    1) $$ ブロックの外にある「行まるごと -- コメント」を除去
    2) $$ ブロックを跨がないように、行末の ; で分割
    """
    lines, in_dollar = [], False
    for line in sql.splitlines():
        if line.count("$$") % 2 == 1:
            in_dollar = not in_dollar
            lines.append(line)
            continue
        if not in_dollar and line.lstrip().startswith("--"):
            continue
        lines.append(line)

    out, buf, in_dollar = [], [], False
    for line in lines:
        if line.count("$$") % 2 == 1:
            in_dollar = not in_dollar
        buf.append(line)
        if not in_dollar and line.rstrip().endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";").strip()
            if stmt:
                out.append(stmt)
            buf = []
    tail = "\n".join(buf).strip().rstrip(";").strip()
    if tail:
        out.append(tail)
    return out


def execute(stmt, wait="50s"):
    res = api("post", "/api/2.0/sql/statements", {
        "statement": stmt, "warehouse_id": WAREHOUSE, "catalog": CATALOG,
        "wait_timeout": wait, "on_wait_timeout": "CONTINUE"})
    if "_cli_error" in res:
        return "CLI_ERROR", res["_cli_error"], None
    sid = res.get("statement_id")
    state = (res.get("status") or {}).get("state")
    while state in ("PENDING", "RUNNING"):
        time.sleep(4)
        res = api("get", f"/api/2.0/sql/statements/{sid}")
        state = (res.get("status") or {}).get("state")
    if state == "SUCCEEDED":
        return "OK", None, res
    msg = ((res.get("status") or {}).get("error") or {}).get("message", "")
    return state or "UNKNOWN", msg[:400], res

def label(stmt):
    m = re.search(r"(?:CREATE OR REPLACE (?:TABLE|VIEW)|ALTER TABLE|CREATE TABLE)\s+`?[\w]*`?\.?`?(\w+)`?\.`?(\w+)`?", stmt)
    kind = stmt.split()[0].upper()
    if m:
        return f"{kind} {m.group(1)}.{m.group(2)}"
    return stmt[:60].replace("\n", " ")

def main():
    paths = sys.argv[1:]
    if not paths:
        print("usage: run_sql.py <file.sql> [...]"); sys.exit(2)
    total_ok = total_err = 0
    for p in paths:
        stmts = split_statements(open(p).read())
        print(f"\n### {p}  ({len(stmts)} 文)")
        for i, s in enumerate(stmts, 1):
            state, err, _ = execute(s)
            if state == "OK":
                total_ok += 1
                print(f"  [{i:3d}/{len(stmts)}] OK   {label(s)}")
            else:
                total_err += 1
                print(f"  [{i:3d}/{len(stmts)}] {state}  {label(s)}\n        {err}")
    print(f"\n==== 成功 {total_ok} / 失敗 {total_err} ====")
    sys.exit(1 if total_err else 0)

if __name__ == "__main__":
    main()
