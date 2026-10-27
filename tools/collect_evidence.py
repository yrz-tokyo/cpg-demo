#!/usr/bin/env python3
"""
FE Bar 用のエビデンスを集めて、サイズ制限の中に収める。

制限（FE Bar FAQ）
  読まれるのは 30ファイルまで / 1ファイル 9,000字まで / 合計 90,000字まで
前ビルドは evidence 20ファイル・149,405字で上限の1.66倍だった。読まれたかどうかは運任せだった。
今回は **12ファイル以内・各6,000字以内・合計60,000字以内** を自分で守る（残りを README とコードに空ける）。

各証跡は「出力そのもの」を載せる。長い結果は先頭N行＋要約統計に落とす。
"""
import json, subprocess, sys, time
from pathlib import Path

PROFILE = "fe-vm-serverless-rongzi-cpg-general"
WAREHOUSE = "2e13820648d1b0bf"
CATALOG = "rongzi_catalog_dev"
PIPELINE = "5824de8f-e369-47f9-8844-abd16c5892f7"
BASE = Path(__file__).resolve().parent.parent
EV = BASE / "evidence"

MAX_PER_FILE = 6000
MAX_TOTAL = 60000
MAX_FILES = 12


def api(method, path, payload=None):
    cmd = ["databricks", "api", method, path, "--profile", PROFILE]
    if payload is not None:
        cmd += ["--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {"_error": (r.stderr or r.stdout).strip()[:300]}
    try:
        return json.loads(r.stdout or "{}")
    except Exception:
        return {"_raw": r.stdout[:300]}


def q(stmt, limit_rows=25):
    """SQL を実行して、列名つきのテキスト表を返す。"""
    res = api("post", "/api/2.0/sql/statements", {
        "statement": stmt, "warehouse_id": WAREHOUSE, "catalog": CATALOG,
        "wait_timeout": "50s", "on_wait_timeout": "CONTINUE"})
    sid = res.get("statement_id")
    state = (res.get("status") or {}).get("state")
    while state in ("PENDING", "RUNNING"):
        time.sleep(3)
        res = api("get", f"/api/2.0/sql/statements/{sid}")
        state = (res.get("status") or {}).get("state")
    if state != "SUCCEEDED":
        err = ((res.get("status") or {}).get("error") or {}).get("message", "")
        return f"!! {state}: {err[:200]}"
    man = res.get("manifest") or {}
    cols = [c["name"] for c in (man.get("schema") or {}).get("columns", [])]
    rows = ((res.get("result") or {}).get("data_array")) or []
    out = [" | ".join(cols)]
    for r in rows[:limit_rows]:
        out.append(" | ".join("" if x is None else str(x) for x in r))
    if len(rows) > limit_rows:
        out.append(f"... ({len(rows)} 行中 {limit_rows} 行を表示)")
    return "\n".join(out)


def sec(title, body):
    return f"### {title}\n```\n{body}\n```\n"


# ----------------------------------------------------------------- 各証跡
def ev_01_data_generation():
    gen = json.loads((BASE / "02_data" / "generated.json").read_text())
    tot = sum(g["rows"] for g in gen)
    lines = [f"# 01 合成データ生成", "",
             f"生成器: 02_data/generate.py + business.py（stdlib のみ・SEED 固定で決定論）",
             f"列の値域は業界データモデル(ECM)の列コメント `Valid values are ...` から取得（自作していない）",
             "", sec("生成結果", "\n".join(
                 f"{g['table']:36s} {g['rows']:7,d} 行 x {g['cols']:3d} 列  {g['bytes']/1024:8.0f} KB"
                 for g in gen) + f"\n{'合計':36s} {tot:7,d} 行")]
    lines.append(sec("Volume 上の着地（フィード単位ディレクトリ）",
                     subprocess.run(["databricks", "fs", "ls",
                                     f"dbfs:/Volumes/{CATALOG}/ops_landing/raw",
                                     "--profile", PROFILE],
                                    capture_output=True, text=True).stdout[:1200]))
    return "01_data_generation.md", "\n".join(lines)


def ev_02_lakeflow():
    ev = api("get", f"/api/2.0/pipelines/{PIPELINE}/events?max_results=250")
    items = ev.get("events", []) if isinstance(ev, dict) else []
    flows = {}
    for e in items:
        d = e.get("details") or {}
        fp = d.get("flow_progress") or {}
        m = fp.get("metrics") or {}
        name = (e.get("origin") or {}).get("flow_name")
        if name and m.get("num_output_rows") is not None:
            flows[name] = max(flows.get(name, 0), m["num_output_rows"])
    dq = []
    for e in items:
        fp = ((e.get("details") or {}).get("flow_progress") or {})
        for exp in (fp.get("data_quality") or {}).get("expectations", []):
            dq.append((((e.get("origin") or {}).get("flow_name")) or "",
                       exp.get("name"), exp.get("passed_records"), exp.get("failed_records")))
    lines = ["# 02 Lakeflow（bronze → silver → gold）", "",
             f"pipeline_id = {PIPELINE} / serverless / photon",
             "bronze 24 STREAMING TABLE / silver 24 MATERIALIZED VIEW / gold 8 MATERIALIZED VIEW",
             "silver は PK 24・FK 53・expectations 25 をパイプライン定義で宣言", ""]
    lines.append(sec("層別オブジェクト数と行数", q(f"""
SELECT table_schema, table_type, COUNT(*) AS objects
FROM {CATALOG}.information_schema.tables
WHERE table_schema <> 'information_schema' AND table_name NOT LIKE '__materialization%'
GROUP BY 1,2 ORDER BY 1,2""", 30)))
    if flows:
        top = sorted(flows.items(), key=lambda x: -x[1])[:22]
        lines.append(sec("フロー別 出力行数", "\n".join(f"{k:46s} {v:>9,d}" for k, v in top)))
    if dq:
        lines.append(sec("expectations 結果（イベントログより・合格/不合格レコード数）",
                         "\n".join(f"{a.split('.')[-1]:28s} {b:26s} pass={c} fail={d}"
                                   for a, b, c, d in dq[:20])))
    # イベント窓に依存しない決定論的な証跡: bronze と silver の行数差 = 落ちた行
    pairs = [("sap_sd__order_raw", "sales_core.order"),
             ("sap_fi__ar_invoice_raw", "finance_core.ar_invoice"),
             ("sap_fi__ap_invoice_raw", "finance_core.ap_invoice"),
             ("pos_edi852__pos_transaction_raw", "sales_core.pos_transaction"),
             ("sap_mm__purchase_order_raw", "procure_core.purchase_order"),
             ("tpm__settlement_raw", "trade_core.settlement"),
             ("tpm__deduction_raw", "trade_core.deduction"),
             ("sap_mm__sku_raw", "master_core.sku"),
             ("salesforce__account_raw", "sales_core.account"),
             ("sap_co__product_standard_cost_raw", "master_core.product_standard_cost")]
    sel = " UNION ALL ".join(
        f"SELECT '{silver}' AS tbl, "
        f"(SELECT count(*) FROM {CATALOG}.ops_landing.{bz}) AS bronze_rows, "
        f"(SELECT count(*) FROM {CATALOG}.{silver}) AS silver_rows"
        for bz, silver in pairs)
    lines.append(sec("expectations の効果（bronze → silver で落ちた行）",
                     q(f"SELECT tbl, bronze_rows, silver_rows, bronze_rows - silver_rows AS dropped, "
                       f"round((bronze_rows - silver_rows)/bronze_rows*100,2) AS dropped_pct "
                       f"FROM ({sel}) ORDER BY dropped DESC", 12)))
    return "02_lakeflow.md", "\n".join(lines)


def ev_03_unity_catalog():
    lines = ["# 03 Unity Catalog（制約・コメント・タグ・ドメイン）", "",
             "ドメインはアカウント上限(1000/1000)のため親1本のみ。部門は governed tag の許可値で表現。",
             "カタログにはドメインタグを付けない（継承が剥がせないため）。", ""]
    lines.append(sec("スキーマへのタグ付与", q(f"""
SELECT schema_name, tag_name, tag_value FROM {CATALOG}.information_schema.schema_tags
ORDER BY schema_name, tag_name""", 24)))
    lines.append(sec("PK / FK 制約（パイプライン定義で宣言したもの）", q(f"""
SELECT constraint_type, COUNT(*) AS n
FROM {CATALOG}.information_schema.table_constraints
WHERE constraint_schema LIKE '%_core' GROUP BY 1 ORDER BY 1""", 10)))
    lines.append(sec("silver の列数（ECM の926列が維持されているか）", q(f"""
SELECT table_schema, COUNT(DISTINCT table_name) AS tables, COUNT(*) AS columns
FROM {CATALOG}.information_schema.columns
WHERE table_schema LIKE '%_core' AND table_name NOT LIKE '__materialization%'
GROUP BY 1 ORDER BY 1""", 10)))
    lines.append(sec("列コメントが維持されている例（ECM 由来・値域つき）", q(f"""
SELECT table_name, column_name, substr(comment,1,110) AS comment
FROM {CATALOG}.information_schema.columns
WHERE table_schema='sales_core' AND table_name='order'
  AND column_name IN ('total_net_amount','total_gross_amount','order_status','channel')""", 6)))
    return "03_unity_catalog.md", "\n".join(lines)


def ev_04_conflict():
    lines = ["# 04 定義衝突（業界データモデルに素で存在する）", "",
             "ECM の metric view は `total_net_amount` / `total_gross_amount` という",
             "完全同名の measure を sales / finance / trade / procurement の4ドメインに持つ。",
             "うち2つ（ap_invoice, purchase_order）は売上ですらない。衝突は仕込みではない。", ""]
    for mv, label in [("sales_mart.sales_order", "受注（営業）"),
                      ("finance_mart.finance_ar_invoice", "純売上（財務）★正本"),
                      ("trade_mart.trade_settlement", "販促精算（販促・売上でない）"),
                      ("finance_mart.finance_ap_invoice", "買掛（財務・売上でない）"),
                      ("procure_mart.procurement_purchase_order", "発注（調達・売上でない）")]:
        v = q(f"SELECT round(MEASURE(total_net_amount)/1e8,1) AS oku FROM {CATALOG}.{mv}", 2)
        lines.append(f"- `{mv}.total_net_amount` = {v.splitlines()[-1]} 億円  — {label}")
    lines.append("")
    lines.append(sec("xdept_mart.mart_revenue_definitions（月次で5つの数字を並べた横断マート）", q(f"""
SELECT date_format(month_start,'yyyy-MM') AS mo,
  round(sales_order_net_amount/1e8,1)            AS order_net,
  round(invoiced_gross_amount/1e8,1)       AS invoiced,
  round(revenue_net_amount/1e8,1)          AS revenue_net,
  round(promo_settlement_net_amount/1e8,1) AS promo_settle,
  round(payable_net_amount/1e8,1)          AS payable,
  round(purchase_order_net_amount/1e8,1)   AS po,
  round(panel_sellout_amount/1e8,1)        AS panel,
  revenue_to_order_ratio
FROM {CATALOG}.xdept_mart.mart_revenue_definitions ORDER BY month_start""", 13)))
    return "04_definition_conflict.md", "\n".join(lines)


def ev_05_xdept():
    lines = ["# 05 部門横断（hub キーで3部門を貫く）", "",
             "hub キー account_id が 営業（受注・店頭）× 財務（請求・未回収）× 販促（販促費・精算・控除）を貫く。", ""]
    lines.append(sec("mart_customer_360（純売上転換率が低い得意先）", q(f"""
SELECT account_name, channel,
  round(sales_order_net_amount/1e8,2)    AS order_net,
  round(revenue_net_amount/1e8,2)  AS revenue_net,
  revenue_to_order_ratio, leakage_ratio,
  round(promo_spend_net_amount/1e8,2) AS promo_spend
FROM {CATALOG}.xdept_mart.mart_customer_360
WHERE sales_order_net_amount IS NOT NULL ORDER BY revenue_to_order_ratio ASC LIMIT 12""", 13)))
    lines.append(sec("業務的な妥当性（純売上を100としたとき）", q(f"""
SELECT
  round(sum(revenue_net_amount)/1e8,1)                                      AS revenue_net_oku,
  round(sum(purchase_order_net_amount)/sum(revenue_net_amount)*100,1)       AS cogs_pct,
  round(sum(promo_settlement_net_amount)/sum(revenue_net_amount)*100,1)     AS promo_settle_pct,
  round(sum(sales_order_net_amount)/sum(revenue_net_amount)*100,1)                AS order_pct
FROM {CATALOG}.xdept_mart.mart_revenue_definitions""", 3)))
    return "05_cross_department.md", "\n".join(lines)


def pg(sql):
    """Lakebase に psql で問い合わせる（トークンは毎回取り直す）。"""
    host = api("get", "/api/2.0/database/instances/brickshouse").get("read_write_dns")
    if not host:
        out = subprocess.run(["databricks", "database", "get-database-instance", "brickshouse",
                              "--profile", PROFILE, "-o", "json"], capture_output=True, text=True)
        try:
            host = json.loads(out.stdout)["read_write_dns"]
        except Exception:
            return "!! Lakebase のホストが取れない"
    import uuid
    tk = subprocess.run(["databricks", "database", "generate-database-credential",
                         "--json", json.dumps({"instance_names": ["brickshouse"],
                                               "request_id": str(uuid.uuid4())}),
                         "--profile", PROFILE, "-o", "json"], capture_output=True, text=True)
    try:
        token = json.loads(tk.stdout)["token"]
    except Exception:
        return "!! Lakebase の認証情報が取れない"
    env = {"PGPASSWORD": token, "PGSSLMODE": "require", "PATH": "/opt/homebrew/bin:/usr/bin:/bin"}
    r = subprocess.run(["psql", "-h", host, "-p", "5432", "-U", "rongzi.yan@databricks.com",
                        "-d", "databricks_postgres", "-c", sql],
                       capture_output=True, text=True, env=env)
    return (r.stdout or r.stderr).strip()[:1800]


def ev_06_lakebase():
    lines = ["# 06 Lakebase（統治ループの人間側の状態）", "",
             "インスタンス `brickshouse` / CU_1 / PG16 / us-east-1",
             "",
             "**なぜ Delta テーブルではないのか**",
             "1. 行単位の更新が頻発（1つの衝突の状態が 検出→調査中→正本決定→公開 と何度も書き換わる）",
             "2. 同時更新がある（営業部長と財務部長が別々の行に自分の主張を書く）",
             "3. **read-modify-write がある**（検出バッチが毎回「却下済み」を読んで次の提案から除外）",
             "4. アプリがサブ秒で読み書きする",
             "バッチ分析用のテーブルでは 1〜4 が成立しない。", ""]
    lines.append(sec("作成したオブジェクト", pg(
        "SELECT table_schema||'.'||table_name FROM information_schema.tables "
        "WHERE table_schema IN ('semantics','app') ORDER BY 1")))
    lines.append(sec("衝突と人の判断（往復の結果）", pg(
        "SELECT c.term, c.status, c.ml_score, d.decision, d.decided_by "
        "FROM semantics.conflict c LEFT JOIN semantics.decision d USING (conflict_id) "
        "ORDER BY c.ml_score DESC")))
    lines.append(sec("「売上」の候補（レビュー画面に並べる内容）", pg(
        "SELECT department, role, substr(object_name,20) AS object, "
        "round(observed_value/1e8,1) AS oku_yen FROM semantics.conflict_candidate cc "
        "JOIN semantics.conflict c USING (conflict_id) "
        "WHERE c.term_normalized='uriage' ORDER BY observed_value DESC")))
    lines.append(sec("ML 教師データ（decision から機械的に導出＝ループが閉じている証跡）", pg(
        "SELECT term_normalized, measure_name, label_is_real_conflict, "
        "evidence->>'value_spread_ratio' AS value_spread FROM semantics.ml_training_label "
        "ORDER BY label_is_real_conflict DESC")))
    lines.append(sec("検出器が次回読む「却下済み」制約（再提案しないための入力）", pg(
        "SELECT term_normalized, measure_name, reason FROM semantics.rejected_pair")))
    return "06_lakebase.md", "\n".join(lines)


COLLECTORS = [ev_01_data_generation, ev_02_lakeflow, ev_03_unity_catalog,
              ev_04_conflict, ev_05_xdept, ev_06_lakebase]


def main():
    EV.mkdir(parents=True, exist_ok=True)
    total, written = 0, []
    for fn in COLLECTORS:
        name, body = fn()
        if len(body) > MAX_PER_FILE:
            body = body[:MAX_PER_FILE - 80] + "\n\n... (ファイル上限 6,000字で切り詰め)"
        (EV / name).write_text(body)
        total += len(body)
        written.append((name, len(body)))
        print(f"  {name:34s} {len(body):6,d} 字")
    print(f"\n  {'合計':34s} {total:6,d} 字 / {len(written)} ファイル")
    print(f"  枠: {MAX_FILES} ファイル / 各 {MAX_PER_FILE:,}字 / 合計 {MAX_TOTAL:,}字")
    if total > MAX_TOTAL or len(written) > MAX_FILES:
        print("  !! 枠を超えている。切り詰めが必要")
        sys.exit(1)
    print("  枠内 OK")


if __name__ == "__main__":
    main()
