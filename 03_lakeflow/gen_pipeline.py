#!/usr/bin/env python3
"""
Lakeflow (SDP) パイプライン SQL を schema.json から生成する。

3層:
  bronze  ops_landing.<src>__<entity>_raw   STREAMING TABLE / read_files(csv.gz) / 型は文字列のまま
  silver  <dept>_core.<entity>               MATERIALIZED VIEW / 型変換 + PK/FK + expectations
  gold    <dept>_mart.* / xdept_mart.*        MATERIALIZED VIEW / 用途別マート

PK/FK は MV のため DDL ではなくパイプライン定義側で宣言する。
expectations は「業務的に意味のある制約」だけを置く（飾りの NOT NULL を並べない）。
"""
import json, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "02_data"))
SCHEMA = json.loads((BASE / "02_data" / "schema.json").read_text())
GEN = json.loads((BASE / "02_data" / "generated.json").read_text())
CATALOG = "rongzi_catalog_dev"
VOL = f"/Volumes/{CATALOG}/ops_landing/raw"

# ソースシステムの対応は generate.py を唯一の正とする。
# ここに複製していたせいで、マーケ6テーブルを足したときにパイプラインが24本のまま取り残された。
from generate import SOURCE   # noqa: E402

# 業務的に意味のある expectations（飾りではなく、違反すると分析が壊れるもの）
EXPECT = {
    "sales_core.order": [
        ("net_within_gross", "total_net_amount <= total_gross_amount", "DROP ROW"),
        ("net_non_negative", "total_net_amount >= 0", "DROP ROW"),
        ("has_customer", "account_id IS NOT NULL", "DROP ROW"),
        ("has_placed_date", "placed_timestamp IS NOT NULL", "DROP ROW"),
        ("qty_positive", "total_quantity > 0", None),
    ],
    "finance_core.ar_invoice": [
        ("net_within_gross", "net_amount <= gross_amount", "DROP ROW"),
        ("net_non_negative", "net_amount >= 0", "DROP ROW"),
        # 純売上 = 請求総額 - 販促値引 - 控除 が崩れていたら、売上の定義が壊れている
        ("net_reconciles", "abs(net_amount - (gross_amount - trade_discount_amount - deduction_amount)) < 1", None),
        ("linked_to_order", "order_id IS NOT NULL", None),
        ("open_not_negative", "open_amount >= -1", None),
    ],
    "finance_core.ap_invoice": [
        ("net_within_gross", "net_amount <= gross_amount * 1.001", "DROP ROW"),
        ("has_supplier", "supplier_id IS NOT NULL", None),
    ],
    "procure_core.purchase_order": [
        ("net_within_gross", "net_amount <= po_gross_amount", "DROP ROW"),
        ("received_within_ordered", "total_quantity_received <= total_quantity_ordered", None),
    ],
    "trade_core.settlement": [
        ("settles_to_claim", "abs(net_amount - (original_claim_amount + adjustment_amount)) < 1", "DROP ROW"),
    ],
    "trade_core.deduction": [
        ("net_non_negative", "net_amount >= 0", "DROP ROW"),
    ],
    "sales_core.pos_transaction": [
        ("units_positive", "units_sold > 0", "DROP ROW"),
        ("sales_non_negative", "dollar_sales >= 0", "DROP ROW"),
        ("panel_source_known", "data_source IS NOT NULL", None),
    ],
    "master_core.sku": [
        ("has_code", "sku_code IS NOT NULL", "DROP ROW"),
        ("status_known", "product_status IN ('active','discontinued','pending','phase_out')", None),
    ],
    "sales_core.account": [
        ("channel_known", "channel IN ('SM','CVS','DgS','卸','EC')", None),
        ("has_name", "account_name IS NOT NULL", "DROP ROW"),
    ],
    "master_core.product_standard_cost": [
        ("unit_cost_positive", "total_standard_cost_per_unit > 0", "DROP ROW"),
    ],
    "finance_core.finance_standard_cost": [
        ("unit_price_positive", "standard_price_per_unit > 0", "DROP ROW"),
    ],
    # --- マーケ ---
    "marketing_core.campaign": [
        # 代理店請求の二重計上。計画の2倍を超える投下は執行ミスとして落とす
        ("spend_within_tolerance", "actual_spend_usd <= planned_budget_usd * 1.25", "DROP ROW"),
        ("spend_non_negative", "actual_spend_usd >= 0", "DROP ROW"),
        ("has_end_date", "end_date IS NOT NULL", "DROP ROW"),
        # 通貨が落ちた行は落とさず警告にする。落とすと投下額が過少になり、
        # 「通貨が無いことに気づかないまま集計する」という本当の事故が再現できない
        ("currency_declared", "currency_code IS NOT NULL AND currency_code <> ''", None),
    ],
    "marketing_core.media_spend": [
        ("spend_non_negative", "actual_spend_amount >= 0", "DROP ROW"),
        ("currency_declared", "currency_code IS NOT NULL AND currency_code <> ''", None),
        ("impressions_when_spent", "actual_spend_amount = 0 OR impressions > 0", None),
    ],
    "marketing_core.consumer_insight": [
        # 調査費のマイナス（ベンダーのクレジットノート）は silver に入れない
        ("spend_non_negative", "actual_spend_usd >= 0", "DROP ROW"),
        ("has_deliverable_date", "deliverable_date IS NOT NULL", None),
    ],
    "marketing_core.campaign_execution": [
        ("spend_non_negative", "actual_spend_amount >= 0", "DROP ROW"),
        ("linked_to_campaign", "campaign_id IS NOT NULL", "DROP ROW"),
        ("delivery_when_spent", "actual_spend_amount = 0 OR impressions_delivered > 0", None),
    ],
    "marketing_core.syndicated_market_data": [
        ("share_within_100", "dollar_share_pct <= 100", "DROP ROW"),
        ("has_period_end", "period_end_date IS NOT NULL", "DROP ROW"),
        ("sales_non_negative", "dollar_sales >= 0", None),
    ],
}


def esc(s):
    return (s or "").replace("'", "''")


def cast_expr(col):
    n, t = col["name"], col["type"]
    if t == "BIGINT" or t == "INT":
        return f"TRY_CAST(`{n}` AS {t}) AS `{n}`"
    if t.startswith("DECIMAL") or t == "DOUBLE":
        return f"TRY_CAST(`{n}` AS {t}) AS `{n}`"
    if t == "BOOLEAN":
        return f"TRY_CAST(lower(`{n}`) IN ('true','1','yes') AS BOOLEAN) AS `{n}`"
    if t == "DATE":
        return f"TRY_CAST(nullif(`{n}`,'') AS DATE) AS `{n}`"
    if t == "TIMESTAMP":
        return f"TRY_CAST(nullif(`{n}`,'') AS TIMESTAMP) AS `{n}`"
    return f"nullif(`{n}`, '') AS `{n}`"


def bronze(key, meta):
    src = SOURCE[key]
    feed = f"{src}__{meta['schema']}__{meta['name']}"   # ランディングはフィード単位のディレクトリ
    bz = f"{src}__{meta['name']}_raw"
    return f"""-- bronze: {src} / {meta['name']}  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `{CATALOG}`.`ops_landing`.`{bz}`
COMMENT 'Bronze。{src} から取り込んだ {meta['name']} の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  '{src}'               AS _source_system
FROM STREAM read_files(
  '{VOL}/{feed}/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);
"""


# パイプラインが所有する MV のコメントは定義に含まれるため、ALTER で変えても
# 次回実行で上書きされる。恒久的に真であるデータの性質はここ（定義側）に書く。
# 統治トグル（03_governance_on.sql）は metric view のコメントと認定タグだけを扱う。
PERMANENT_NOTE = {
    # ここに書くのは **データの構造的事実** だけ。統治前の状態でも真であるもの。
    # 「どれが正本か」は統治の判断なので metric view のコメント（統治トグル側）で表現する。
    "sales_core.pos_transaction":
        "【データの出所】Nielsen の syndicated パネル。全店 census ではなく約15% ACV の投影値。",
    "sales_core.order":
        "【粒度】受注はヘッダ粒度で sku_id を持たない（ECM の sales ドメインに order_line が無い）。"
        "商品軸の分析は pos_transaction / distribution_point / promotion_line を使う。",
    "marketing_core.campaign":
        "【通貨】金額列は USD 建て（currency_code）。営業・財務・販促は JPY 建てなので、"
        "この表の金額を他部門の金額と直接足したり割ったりはできない。",
    "marketing_core.media_spend":
        "【通貨】金額列は USD 建て（currency_code）。"
        "【粒度】媒体の購入明細。campaign_id でキャンペーンにロールアップする。",
    "marketing_core.campaign_execution":
        "【通貨】金額列は USD 建て（spend_currency_code）。"
        "【粒度】配信の執行明細。campaign_id でキャンペーンにロールアップする。",
    "marketing_core.consumer_insight":
        "【内容】消費者調査プロジェクトの費用（USD）。媒体やキャンペーンへの投下額ではない。",
    # ここは構造的事実だけ。「自社売上にはどの表を使うか」は統治の判断なので書かない
    # （書くと統治前の状態に答えが混ざり、before/after が測れなくなる）。
    "marketing_core.syndicated_market_data":
        "【データの出所】Nielsen Scantrack の syndicated データ。"
        "【粒度】ブランド × 地域 × 週。market_name は8地域で、合計が全国の universe になる。"
        "【単位】金額列は USD。",
}


# business.py で値を業務的に上書きした列は、ECM のコメントが宣言している値域と実データがずれる。
# ずれたままにすると Genie がコメントを信じて WHERE 句を組み、正しい質問に 0 件で答える
# （sales_core.order.channel が実際にそうだった: 宣言 retail|wholesale… / 実データ SM|CVS|DgS|卸|EC）。
# tools/sync_value_domains.py が汚れ無しデータから実際の値を拾って、ここに流し込む。
_vd_path = BASE / "02_data" / "value_domains_actual.json"
VALUE_DOMAIN_ACTUAL = json.loads(_vd_path.read_text()) if _vd_path.exists() else {}
_VALID = re.compile(r"Valid values are\s*`[^`]*`")


def fix_domain(key, col, comment):
    """列コメントの値域宣言を実データに合わせる。宣言が無い列には追記する。"""
    vals = (VALUE_DOMAIN_ACTUAL.get(key) or {}).get(col)
    if not vals:
        return comment
    decl = "Valid values are `" + "|".join(vals) + "`"
    if _VALID.search(comment):
        return _VALID.sub(decl, comment)
    sep = "" if comment.rstrip().endswith((".", "。")) else "."
    return f"{comment.rstrip()}{sep} {decl}"


def silver(key, meta):
    src = SOURCE[key]
    bz = f"{src}__{meta['name']}_raw"
    # PK 列は NOT NULL が必須（SDP の仕様）
    pkset = set(meta["pk"])
    cols = []
    for c in meta["columns"]:
        nn = " NOT NULL" if c["name"] in pkset else ""
        cm = fix_domain(key, c["name"], c["comment"] or "")
        cols.append(f"  `{c['name']}` {c['type']}{nn} COMMENT '{esc(cm)}'")
    # 順序は 列 → EXPECT → table_constraint（PK/FK）。制約名はバッククォートを付けない。
    exps = []
    for name, expr, action in EXPECT.get(key, []):
        a = f" ON VIOLATION {action}" if action else ""
        exps.append(f"  CONSTRAINT ex_{name} EXPECT ({expr}){a}")
    cons = []
    if meta["pk"]:
        pkc = ", ".join(f"`{c}`" for c in meta["pk"])
        cons.append(f"  CONSTRAINT pk_{meta['name']} PRIMARY KEY({pkc})")
    self_key = f"{meta['schema']}.{meta['name']}"
    for fk in meta["fks"]:
        # 自己参照FK は SDP が循環と判定して update 全体を落とすので宣言しない
        # (sales_core.invoice.original_invoice_id / master_core.category.parent_category_id)
        if fk["parent"] == self_key:
            continue
        pcols = ", ".join(f"`{c}`" for c in fk["parent_columns"])
        ccols = ", ".join(f"`{c}`" for c in fk["columns"])
        pschema, ptable = fk["parent"].split(".")
        cons.append(f"  CONSTRAINT {fk['name']} FOREIGN KEY ({ccols}) "
                    f"REFERENCES `{CATALOG}`.`{pschema}`.`{ptable}`({pcols}) NOT ENFORCED")
    body = ",\n".join(cols + exps + cons)
    sel = ",\n  ".join(cast_expr(c) for c in meta["columns"])
    return f"""-- silver: {meta['schema']}.{meta['name']}  （型変換 + PK/FK + expectations）
CREATE OR REFRESH MATERIALIZED VIEW `{CATALOG}`.`{meta['schema']}`.`{meta['name']}` (
{body}
)
COMMENT '{esc((PERMANENT_NOTE.get(key, '') + ' ' + meta['comment']).strip())[:1400]}'
AS SELECT
  {sel}
FROM `{CATALOG}`.`ops_landing`.`{bz}`;
"""


def main():
    out_b, out_s = [], []
    for key in SOURCE:
        meta = SCHEMA[key]
        out_b.append(bronze(key, meta))
        out_s.append(silver(key, meta))
    hdr = ("-- 自動生成: 03_lakeflow/gen_pipeline.py\n"
           "-- Brickshouse Food and Beverage / Lakeflow Spark Declarative Pipeline\n"
           f"-- bronze {len(out_b)} 本 → silver {len(out_s)} 本\n"
           "-- 列名・型・コメントは業界データモデル(ECM)由来。expectations は自作。\n\n")
    (BASE / "03_lakeflow" / "01_bronze.sql").write_text(hdr + "\n".join(out_b))
    (BASE / "03_lakeflow" / "02_silver.sql").write_text(hdr + "\n".join(out_s))
    nexp = sum(len(v) for v in EXPECT.values())
    print(f"01_bronze.sql : {len(out_b)} streaming table")
    print(f"02_silver.sql : {len(out_s)} materialized view "
          f"(PK {sum(1 for k in SOURCE if SCHEMA[k]['pk'])} / "
          f"FK {sum(len(SCHEMA[k]['fks']) for k in SOURCE)} / expectations {nexp})")

if __name__ == "__main__":
    main()
