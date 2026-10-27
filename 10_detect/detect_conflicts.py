#!/usr/bin/env python3
"""
定義の衝突を検出して Lakebase に書く。

やっていること
  1. metric view の measure 名を全部集め、**2つ以上のオブジェクトに同名がある**ものを拾う
  2. 各オブジェクトで MEASURE() を実行して、その定義で出る実測値を取る
     （MEASURE() が通ることが「それが本当に measure である」証明にもなる）
  3. semantics.rejected_pair にある組み合わせは捨てる ← ループの折り返し点。
     人が「これは衝突ではない」と言ったものを二度と上げない
  4. 業務用語（term_normalized）と根拠文を LLM に書かせる
  5. semantics.conflict / conflict_candidate に upsert する

検出は「同名の measure」という機械的な事実から始める。意味の判断は人に渡す。
LLM は言葉を付けるだけで、衝突かどうかを決めない。

使い方
  python3 10_detect/detect_conflicts.py            # 検出して Lakebase に書く
  python3 10_detect/detect_conflicts.py --dry-run  # 書かずに結果だけ出す
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PROFILE = "fe-vm-serverless-rongzi-cpg-general"
WAREHOUSE = "2e13820648d1b0bf"
CATALOG = "rongzi_catalog_dev"
INSTANCE = "brickshouse"
DBNAME = "databricks_postgres"
DETECTOR_VERSION = "v2-measure-collision"
LLM = "databricks-claude-sonnet-4-5"

# 数値型の measure だけを対象にする。ID 列や日付は衝突の話にならない。
NUMERIC = ("DOUBLE", "DECIMAL", "LONG", "INT", "FLOAT", "BIGINT", "SMALLINT")
# measure 名に見えても実体が ID のものは外す
SKIP_SUFFIX = ("_id", "_code", "_pct_id")


def api(method, path, payload=None):
    cmd = ["databricks", "api", method, path, "--profile", PROFILE]
    if payload is not None:
        cmd += ["--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {"_err": (r.stderr or r.stdout).strip()[:400]}
    return json.loads(r.stdout or "{}")


def sql(stmt: str, timeout_s: int = 120):
    res = api("post", "/api/2.0/sql/statements", {
        "statement": stmt, "warehouse_id": WAREHOUSE, "catalog": CATALOG,
        "wait_timeout": "30s", "on_wait_timeout": "CONTINUE"})
    if "_err" in res:
        raise RuntimeError(res["_err"])
    sid = res.get("statement_id")
    deadline = time.time() + timeout_s
    while (res.get("status") or {}).get("state") in ("PENDING", "RUNNING"):
        if time.time() > deadline:
            raise TimeoutError(stmt[:100])
        time.sleep(1.5)
        res = api("get", f"/api/2.0/sql/statements/{sid}")
    st = (res.get("status") or {}).get("state")
    if st != "SUCCEEDED":
        err = json.dumps((res.get("status") or {}).get("error"), ensure_ascii=False)
        raise RuntimeError(f"{st}: {err[:300]}")
    cols = [c["name"] for c in ((res.get("manifest") or {}).get("schema") or {}).get("columns", [])]
    rows = (res.get("result") or {}).get("data_array") or []
    return [dict(zip(cols, r)) for r in rows]


# ------------------------------------------------------------------ 1) 同名 measure

def collisions() -> dict[str, list[dict]]:
    rows = sql(f"""
        SELECT c.table_schema, c.table_name, c.column_name, c.data_type, c.comment,
               st.tag_value AS department,
               tt.tag_value AS certification
        FROM {CATALOG}.information_schema.columns c
        JOIN {CATALOG}.information_schema.tables t
          ON t.table_schema = c.table_schema AND t.table_name = c.table_name
        LEFT JOIN (SELECT schema_name, max(tag_value) AS tag_value
                   FROM {CATALOG}.information_schema.schema_tags
                   WHERE tag_name = 'brickshouse_department' GROUP BY 1) st
          ON st.schema_name = c.table_schema
        LEFT JOIN (SELECT schema_name, table_name, max(tag_value) AS tag_value
                   FROM {CATALOG}.information_schema.table_tags
                   WHERE tag_name = 'system.certification_status' GROUP BY 1, 2) tt
          ON tt.schema_name = c.table_schema AND tt.table_name = c.table_name
        WHERE t.table_type = 'METRIC_VIEW'
    """)
    by_name: dict[str, list[dict]] = {}
    for r in rows:
        name = r["column_name"]
        if r["data_type"] not in NUMERIC or name.endswith(SKIP_SUFFIX):
            continue
        by_name.setdefault(name, []).append(r)
    return {k: v for k, v in by_name.items() if len(v) > 1}


# ------------------------------------------------------------------ 2) 実測値

def observed(schema: str, table: str, measure: str) -> float | None:
    """その定義で出る値。MEASURE() が通らなければ measure ではないので捨てる。"""
    try:
        rows = sql(f"SELECT MEASURE(`{measure}`) AS v FROM `{CATALOG}`.`{schema}`.`{table}`")
    except Exception:
        return None
    if not rows or rows[0]["v"] is None:
        return None
    try:
        return float(rows[0]["v"])
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ 4) 言葉を付ける

PROMPT = """あなたは日本の食品飲料メーカー（ビール類・清涼飲料・健康食品）のデータスチュワードです。
同じ名前の指標が複数のオブジェクトに存在しています。これに**現場の人が会話で使う言葉**を当て、
なぜ紛らわしいかを1〜2文で書いてください。どれが正本かは**判断しないでください**。

用語の付け方
  - 現場の会話語を使う。例: 売上 / 原価 / 販促費 / マーケ投下額 / 市場規模 / 粗利
  - 列名の直訳は避ける。「正味金額合計」「総額」のような機械的な訳は不可
  - 候補の部門と値の大きさから、その指標が業務で何と呼ばれているかを推測する
  - 10文字以内

measure 名: {measure}
候補:
{cands}

次の JSON だけを返してください。説明文は不要です。
{{"term": "業務用語（日本語・10文字以内・現場の会話語）", "evidence": "なぜ紛らわしいか（1〜2文・日本語）"}}"""


def name_it(measure: str, cands: list[dict]) -> tuple[str, str]:
    lines = []
    for c in cands:
        lines.append(f"- {c['table_schema']}.{c['table_name']}"
                     f"（部門 {c.get('department') or '未設定'}）"
                     f" 値 {c['observed']:,.0f}  説明: {(c.get('comment') or '')[:120]}")
    prompt = PROMPT.format(measure=measure, cands="\n".join(lines))
    # ai_query には文字列リテラルで渡すので、プロンプト側のクォートをエスケープする。
    esc = prompt.replace("\\", "\\\\").replace("'", "''")
    try:
        rows = sql(f"SELECT ai_query('{LLM}', '{esc}') AS out")
        raw = rows[0]["out"] if rows else ""
        m = re.search(r"\{.*\}", raw, re.S)
        d = json.loads(m.group(0)) if m else {}
        return (d.get("term") or measure), (d.get("evidence") or "")
    except Exception as e:
        # LLM が落ちても検出自体は続ける。言葉は後から人が付けられる。
        return measure, f"（用語の自動命名に失敗: {type(e).__name__}）"


# ------------------------------------------------------------------ 5) Lakebase

def lakebase_cmd(sql_text: str) -> str:
    host = api("get", f"/api/2.0/database/instances/{INSTANCE}").get("read_write_dns")
    tok = api("post", "/api/2.0/database/credentials",
              {"instance_names": [INSTANCE], "request_id": str(uuid.uuid4())}).get("token")
    me = api("get", "/api/2.0/preview/scim/v2/Me").get("userName")
    if not (host and tok and me):
        raise RuntimeError("Lakebase の接続情報を取得できませんでした")
    p = Path("/tmp/brickshouse_detect.sql")
    p.write_text(sql_text, encoding="utf-8")
    r = subprocess.run(
        ["psql", "-h", host, "-p", "5432", "-U", me, "-d", DBNAME,
         "-v", "ON_ERROR_STOP=1", "-f", str(p)],
        capture_output=True, text=True,
        env={"PGPASSWORD": tok, "PGSSLMODE": "require", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"})
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[:600])
    return r.stdout


def rejected_pairs() -> set[tuple[str, str, str, str]]:
    try:
        out = lakebase_cmd(
            "\\pset format unaligned\n\\pset tuples_only on\n"
            "SELECT term_normalized||'\\t'||measure_name||'\\t'||object_a||'\\t'||object_b "
            "FROM semantics.rejected_pair;")
    except Exception as e:
        print(f"  ! rejected_pair を読めませんでした（初回なら正常）: {str(e)[:120]}")
        return set()
    out_set = set()
    for line in out.splitlines():
        parts = line.strip().split("\t")
        if len(parts) == 4:
            out_set.add(tuple(parts))
    return out_set


def q(s) -> str:
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-llm", action="store_true", help="用語の自動命名をしない")
    a = ap.parse_args()

    print("1) metric view の同名 measure を探す")
    cols = collisions()
    print(f"   同名が2つ以上あった measure: {len(cols)} 件")

    print("2) 各定義の実測値を取る（MEASURE() が通るかの検証も兼ねる）")
    found = {}
    for measure, cands in sorted(cols.items()):
        live = []
        for c in cands:
            v = observed(c["table_schema"], c["table_name"], measure)
            if v is None:
                continue
            live.append({**c, "observed": v})
        if len(live) > 1:
            found[measure] = live
            spread = max(x["observed"] for x in live) / max(1e-9, min(x["observed"] for x in live))
            print(f"   {measure:28s} {len(live)}件  最大/最小 = {spread:,.1f}倍")
    print(f"   実際に衝突しているもの: {len(found)} 件")

    print("3) 却下済みのペアを除く")
    rejected = rejected_pairs()
    print(f"   却下済みペア: {len(rejected)} 件")

    print("4) 業務用語と根拠文を付ける")
    items = []
    for measure, cands in found.items():
        term, evidence = (measure, "") if a.no_llm else name_it(measure, cands)
        names = sorted(f"{c['table_schema']}.{c['table_name']}" for c in cands)
        if any((term, measure, names[i], names[j]) in rejected
               for i in range(len(names)) for j in range(i + 1, len(names))):
            print(f"   - {term} / {measure} は却下済みのため出さない")
            continue
        items.append({"term": term, "measure": measure, "evidence": evidence,
                      "candidates": cands})
        print(f"   {term:12s} <- {measure}  : {evidence[:90]}")

    if a.dry_run:
        print("\n--dry-run なので Lakebase には書きません")
        print(json.dumps([{k: v for k, v in it.items() if k != "candidates"} for it in items],
                         ensure_ascii=False, indent=1))
        return 0

    print("5) Lakebase に upsert する")
    stmts = ["BEGIN;"]
    for it in items:
        vals = [c["observed"] for c in it["candidates"]]
        spread = max(vals) / max(1e-9, min(vals))
        # evidence は JSONB。文章だけでなく、測った事実（候補数・最大最小比・各値）も入れる。
        # 人が画面で判断するとき、文章より数字のほうが効く。
        ev = {
            "summary": it["evidence"],
            "candidate_count": len(it["candidates"]),
            "max_over_min": round(spread, 2),
            "values": {f"{c['table_schema']}.{c['table_name']}": round(c["observed"], 2)
                       for c in it["candidates"]},
            "departments": sorted({(c.get("department") or "未設定") for c in it["candidates"]}),
            "detector": DETECTOR_VERSION,
        }
        norm = re.sub(r"\s+", "", it["term"]).lower()
        stmts.append(f"""
INSERT INTO semantics.conflict
  (term, term_normalized, measure_name, status, evidence, ml_score, detector_version)
VALUES ({q(it['term'])}, {q(norm)}, {q(it['measure'])}, 'detected',
        {q(json.dumps(ev, ensure_ascii=False))}::jsonb,
        {min(0.99, 0.4 + 0.1 * len(it['candidates']) + min(0.3, spread / 100)):.4f},
        {q(DETECTOR_VERSION)})
ON CONFLICT (term_normalized, measure_name, detector_version) DO UPDATE
  SET term = EXCLUDED.term, evidence = EXCLUDED.evidence,
      ml_score = EXCLUDED.ml_score, updated_at = now();""")
        for c in it["candidates"]:
            obj = f"{c['table_schema']}.{c['table_name']}"
            stmts.append(f"""
INSERT INTO semantics.conflict_candidate
  (conflict_id, object_name, object_type, department, measure_expr, role, observed_value, note)
SELECT conflict_id, {q(obj)}, 'METRIC_VIEW', {q(c.get('department'))},
       {q(f"MEASURE({it['measure']})")},
       {q('authoritative' if c.get('certification') == 'certified' else 'candidate')},
       {c['observed']:.2f}, {q((c.get('comment') or '')[:400])}
FROM semantics.conflict
WHERE term_normalized = {q(norm)} AND measure_name = {q(it['measure'])}
  AND detector_version = {q(DETECTOR_VERSION)}
ON CONFLICT (conflict_id, object_name) DO UPDATE
  SET observed_value = EXCLUDED.observed_value, role = EXCLUDED.role,
      department = EXCLUDED.department, note = EXCLUDED.note;""")
    stmts.append("COMMIT;")
    out = lakebase_cmd("\n".join(stmts))
    print(out[-400:] if out else "   (出力なし)")

    chk = lakebase_cmd(
        "\\pset format aligned\n"
        "SELECT c.term, c.measure_name, c.status, round(c.ml_score,2) AS score, "
        "count(k.candidate_id) AS cands "
        "FROM semantics.conflict c LEFT JOIN semantics.conflict_candidate k "
        "  ON k.conflict_id = c.conflict_id "
        "GROUP BY 1,2,3,4 ORDER BY 4 DESC;")
    print(chk)
    return 0


if __name__ == "__main__":
    sys.exit(main())
