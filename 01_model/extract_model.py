#!/usr/bin/env python3
"""
Brickshouse Food and Beverage — 業界データモデルからの抽出器

借りたもの: databricks-industry-solutions/lakehouse-industry-data-models
            data-models/food_beverage/v1/ecm  （DDL・列コメント・PK・FK・metric view）
自分で決めたこと: どの24テーブルを採るか / ドメイン→スキーマの対応 / 部門外FKの切り方

ECM は 19ドメイン 376テーブルあるが、フェーズ1は「売上」の定義衝突が成立する
最小集合に絞る。衝突は仕込みではなく、ECM の metric view に素で存在する:
  total_net_amount / total_gross_amount が sales / finance / trade / procurement の
  4ドメインに完全同名で存在し、うち2つ（ap_invoice, purchase_order）は売上ではない。

フェーズ2でマーケを追加して、衝突は4組になった（すべて ECM に素で存在）:
  1. total_net_amount        … sales / finance / trade / procurement（売上）
  2. total_actual_spend_usd  … marketing.campaign（投下） / marketing.consumer_insight（調査費）
  3. 通貨                     … marketing は _usd 建て、sales / finance は JPY
  4. dollar_sales            … sales.pos_transaction（自社の店頭実売・パネル投影値）
                               / marketing.syndicated_market_data（市場全体・競合込み）
"""
import re, sys, os, json
from pathlib import Path

SRC = Path("/tmp/lhidm/data-models/food_beverage/v1/ecm")
OUT = Path(__file__).parent
CATALOG = "rongzi_catalog_dev"

# ドメイン.テーブル -> 配置先スキーマ
#   master_core  : 特定部門が所有しない全社マスタ
#   *_core       : 部門の conformed 層（silver）
PLACEMENT = {
    ("product", "sku"):                    "master_core",
    ("product", "category"):               "master_core",
    ("product", "product_standard_cost"):  "master_core",

    ("sales", "order"):                    "sales_core",
    ("sales", "invoice"):                  "sales_core",
    ("sales", "rep"):                      "sales_core",
    ("sales", "territory"):                "sales_core",
    ("sales", "pos_transaction"):          "sales_core",
    ("sales", "distribution_point"):       "sales_core",
    ("customer", "account"):               "sales_core",

    ("finance", "ar_invoice"):             "finance_core",
    ("finance", "ap_invoice"):             "finance_core",
    ("finance", "gl_account"):             "finance_core",
    ("finance", "cost_center"):            "finance_core",
    ("finance", "profit_center"):          "finance_core",
    ("finance", "finance_standard_cost"):  "finance_core",

    ("trade", "promotion_event"):          "trade_core",
    ("trade", "promotion_line"):           "trade_core",
    ("trade", "settlement"):               "trade_core",
    ("trade", "fund"):                     "trade_core",
    ("trade", "accrual"):                  "trade_core",
    ("trade", "deduction"):                "trade_core",

    ("procurement", "purchase_order"):     "procure_core",
    ("procurement", "supplier"):           "procure_core",

    # フェーズ2: マーケ。brand / campaign は営業・販促・製品が既に参照しているハブで、
    # 足した瞬間に既存テーブルから6本のFK（sku.brand_id / order.campaign_id /
    # promotion_event.campaign_id / promotion_line.brand_id / fund.brand_id /
    # distribution_point.brand_id）がつながる。横から足した部門ではない。
    ("marketing", "brand"):                "marketing_core",
    ("marketing", "campaign"):             "marketing_core",
    ("marketing", "media_spend"):          "marketing_core",
    ("marketing", "consumer_insight"):     "marketing_core",
    ("marketing", "campaign_execution"):   "marketing_core",
    ("marketing", "syndicated_market_data"): "marketing_core",
}

def fq(schema, table):
    return f"`{CATALOG}`.`{schema}`.`{table}`"

def extract_tables():
    """24テーブルの CREATE OR REPLACE TABLE ブロックを抜き、3部名を差し替える。"""
    out, found, missing = [], [], []
    by_domain = {}
    for (dom, tbl) in PLACEMENT:
        by_domain.setdefault(dom, []).append(tbl)

    for dom, tbls in by_domain.items():
        path = SRC / "schemas" / f"food_beverage_{dom}_schema_v1_ecm.sql"
        txt = path.read_text()
        for tbl in tbls:
            pat = (r"CREATE OR REPLACE TABLE `food_beverage_ecm`\.`" + re.escape(dom)
                   + r"`\.`" + re.escape(tbl) + r"` \((.*?)\n\) COMMENT '(.*?)';")
            m = re.search(pat, txt, re.S)
            if not m:
                missing.append(f"{dom}.{tbl}"); continue
            body, comment = m.group(1), m.group(2)
            schema = PLACEMENT[(dom, tbl)]
            ncols = len(re.findall(r"^\s{4}`\w+`", body, re.M))
            out.append(
                f"-- source: ECM {dom}.{tbl}  ({ncols} cols)  -> {schema}.{tbl}\n"
                f"CREATE OR REPLACE TABLE {fq(schema, tbl)} ({body}\n) COMMENT '{comment}';\n"
            )
            found.append((dom, tbl, schema, ncols))
    return out, found, missing

def extract_fks():
    """
    FK は2か所にある: 各ドメインの schema ファイル（ドメイン内）と cross_domain ファイル。
    採用した24テーブルに「親も子も」含まれるものだけ残す。親が subset 外のものは落とす
    （= フェーズ1に存在しないドメインへの参照）。
    """
    files = [SRC / "schemas" / f"food_beverage_{d}_schema_v1_ecm.sql"
             for d in sorted({d for d, _ in PLACEMENT})]
    files.append(SRC / "schemas" / "food_beverage_cross_domain_foreign_keys_v1_ecm.sql")

    alter = re.compile(
        r"ALTER TABLE `food_beverage_ecm`\.`(\w+)`\.`(\w+)` "
        r"ADD CONSTRAINT `?(\w+)`? FOREIGN KEY \(([^)]*)\) "
        r"REFERENCES `food_beverage_ecm`\.`(\w+)`\.`(\w+)`\(([^)]*)\);"
    )
    kept, dropped, seen = [], 0, set()
    for f in files:
        for m in alter.finditer(f.read_text()):
            cd, ct, name, cols, pd_, pt, pcols = m.groups()
            if (cd, ct) not in PLACEMENT or (pd_, pt) not in PLACEMENT:
                dropped += 1; continue
            key = (cd, ct, name)
            if key in seen: continue
            seen.add(key)
            kept.append(
                f"ALTER TABLE {fq(PLACEMENT[(cd,ct)], ct)} ADD CONSTRAINT {name} "
                f"FOREIGN KEY ({cols}) REFERENCES {fq(PLACEMENT[(pd_,pt)], pt)}({pcols});\n"
            )
    return kept, dropped

def main():
    tables, found, missing = extract_tables()
    fks, dropped = extract_fks()

    hdr = ("-- 自動生成: 01_model/extract_model.py\n"
           "-- 出所: databricks-industry-solutions/lakehouse-industry-data-models\n"
           "--       data-models/food_beverage/v1/ecm (ECM: 19 domains / 376 tables)\n"
           f"-- 採用: {len(found)} テーブル / {sum(c for *_, c in found)} 列（列コメント・値域はそのまま維持）\n\n")
    (OUT / "tables.sql").write_text(hdr + "\n".join(tables))
    (OUT / "foreign_keys.sql").write_text(
        hdr + f"-- 採用FK {len(fks)} 本 / 親がフェーズ1外のため落としたFK {dropped} 本\n\n" + "".join(fks))

    print(f"tables.sql       : {len(found)} テーブル / {sum(c for *_, c in found)} 列")
    print(f"foreign_keys.sql : {len(fks)} 本採用 / {dropped} 本は親がフェーズ1外のため除外")
    if missing: print("見つからなかったテーブル:", missing)
    print()
    for dom, tbl, schema, n in sorted(found, key=lambda x: (x[2], x[1])):
        print(f"  {schema:14s} {tbl:24s} <- ECM {dom}.{tbl}  ({n} cols)")
    json.dump([{"domain": d, "table": t, "schema": s, "columns": n} for d, t, s, n in found],
              open(OUT / "manifest.json", "w"), indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()

# --------------------------------------------------------------------------------------
# metric view: ECM のものを「素のまま」移植する。衝突は自作せず、ECM に既に在るものを使う。
# --------------------------------------------------------------------------------------
MART = {"master_core": "master_mart", "sales_core": "sales_mart", "finance_core": "finance_mart",
        "trade_core": "trade_mart", "procure_core": "procure_mart", "marketing_core": "marketing_mart"}

def extract_metric_views():
    src_of = {(d, t): s for (d, t), s in PLACEMENT.items()}
    kept, skipped = [], []
    for dom in sorted({d for d, _ in PLACEMENT}):
        f = SRC / "metrics" / f"food_beverage_{dom}_metrics_v1_ecm.sql"
        if not f.exists():
            continue
        txt = f.read_text()
        for m in re.finditer(
            r"CREATE OR REPLACE VIEW `food_beverage_ecm`\.`_metrics`\.`(\w+)`\s*\n"
            r"WITH METRICS\s*\nLANGUAGE YAML\s*\nAS \$\$\n(.*?)\n\$\$;", txt, re.S):
            view, body = m.group(1), m.group(2)
            sm = re.search(r'source:\s*"`food_beverage_ecm`\.`(\w+)`\.`(\w+)`"', body)
            if not sm:
                skipped.append((view, "source 解析不可")); continue
            sd, st = sm.group(1), sm.group(2)
            if (sd, st) not in src_of:
                skipped.append((view, f"source {sd}.{st} はフェーズ1外")); continue
            core = src_of[(sd, st)]
            newbody = body.replace(sm.group(0), f'source: "{fq(core, st)}"')
            kept.append(
                f"-- source: ECM _metrics.{view}  (over {sd}.{st})  -> {MART[core]}.{view}\n"
                f"CREATE OR REPLACE VIEW {fq(MART[core], view)}\n"
                f"WITH METRICS\nLANGUAGE YAML\nAS $$\n{newbody}\n$$;\n")
    return kept, skipped

if __name__ == "__main__":
    mvs, skipped = extract_metric_views()
    (OUT / "metric_views.sql").write_text(
        "-- 自動生成: 01_model/extract_model.py (extract_metric_views)\n"
        "-- ECM の metric view を素のまま移植。source の3部名のみ差し替える。\n"
        f"-- 採用 {len(mvs)} 本 / source がフェーズ外で落としたもの {len(skipped)} 本\n\n"
        + "\n".join(mvs))
    print(f"\nmetric_views.sql : {len(mvs)} 本採用 / {len(skipped)} 本除外")
    for v, why in skipped:
        print(f"  -- {v}: {why}")
