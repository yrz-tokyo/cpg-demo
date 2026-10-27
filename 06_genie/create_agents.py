#!/usr/bin/env python3
"""
Genie Agent を4本作る（営業 / 財務 / マーケ / 横断）。

部門は 営業(販促を含む) / 財務 / マーケ の3つ。販促は営業部門の中の機能なので、
営業 Agent が sales_core と trade_core の**両方**を持つ。
これは意図的で、`sales_order.total_net_amount`（受注）と
`trade_settlement.total_net_amount`（販促精算）が**同じ Agent の中に同名で並ぶ**。
部門別 Agent の中で定義衝突が起きる状態を作るため（前の構成では
部門ごとに Agent が分かれていたせいで、同名 measure に手が届かず trap_hit が 0/35 だった）。

重要: instructions は **最小** で作る。
  評価ハーネスの「統治前」ベースラインを取るため、この段階では
  「売上の正本はどれか」を一切教えない。instructions の追加は統治ON（07_governance_on）で行う。

Genie Agent が自分のワークスペース内にあること自体が、Genie One のルーティング先を
自分の資産に限定する働きをする（他FEの Agent は別ワークスペースなので候補に入らない）。
"""
import json, subprocess, sys, uuid
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude/plugins/cache/fe-vibe/fe-internal-tools/1.4.7/skills/genie-rooms/resources"))
from genie_space_builder import GenieSpaceBuilder   # noqa: E402

PROFILE = "fe-vm-serverless-rongzi-cpg-general"
WAREHOUSE = "2e13820648d1b0bf"
C = "rongzi_catalog_dev"

SPACES = {
    "営業": {
        "title": "Brickshouse 営業",
        "description": "Brickshouse Food and Beverage の営業部門（販促を含む）。受注・請求・得意先・営業担当・営業地域・店頭実売（Nielsenパネル）・配下店舗、および販促イベント・明細・精算・ファンド・引当・控除。",
        "tables": [f"{C}.sales_core.{t}" for t in
                   ("order", "invoice", "rep", "territory", "pos_transaction",
                    "distribution_point", "account")]
                + [f"{C}.sales_mart.{t}" for t in
                   ("mart_sales_performance", "mart_account_coverage", "sales_order",
                    "sales_invoice", "sales_rep", "customer_account_overview")]
                + [f"{C}.trade_core.{t}" for t in
                   ("promotion_event", "promotion_line", "settlement", "fund",
                    "accrual", "deduction")]
                + [f"{C}.trade_mart.{t}" for t in
                   ("mart_promotion_roi", "mart_trade_spend_flow", "trade_promotion_event",
                    "trade_promotion_line", "trade_settlement", "trade_fund", "trade_accrual")]
                + [f"{C}.master_core.sku", f"{C}.master_core.category",
                   f"{C}.marketing_core.brand", f"{C}.marketing_core.campaign"],
        "samples": [
            "2026年の受注金額が大きい得意先トップ5はどこですか？",
            "販促費をかけた分、売上は増えていますか？",
            "いま未出荷のまま残っている受注で、金額が大きいものを10件出してください。",
        ],
        "governed": [f"{C}.xdept_mart.mart_revenue_definitions",
                     f"{C}.xdept_mart.mart_customer_360"],
    },
    "財務": {
        "title": "Brickshouse 財務",
        "description": "Brickshouse Food and Beverage の財務部門。売掛請求・買掛請求・勘定・原価センター・利益センター・標準原価・売上照合。",
        "tables": [f"{C}.finance_core.{t}" for t in
                   ("ar_invoice", "ap_invoice", "gl_account", "cost_center",
                    "profit_center", "finance_standard_cost")]
                + [f"{C}.finance_mart.{t}" for t in
                   ("mart_revenue_reconciliation", "mart_standard_cost_compare",
                    "finance_ar_invoice", "finance_ap_invoice")]
                + [f"{C}.sales_core.account", f"{C}.sales_core.order",
                   f"{C}.master_core.sku", f"{C}.master_core.product_standard_cost",
                   f"{C}.master_mart.product_standard_cost"],
        "samples": [
            "2026年の純売上はいくらですか？",
            "未回収の売掛金残高はいくらで、得意先別の上位5社はどこですか？",
            "2026年の原価率はいくらですか？",
        ],
        "governed": [f"{C}.xdept_mart.mart_revenue_definitions",
                     f"{C}.xdept_mart.mart_customer_360"],
    },
    "マーケ": {
        "title": "Brickshouse マーケティング",
        "description": "Brickshouse Food and Beverage のマーケティング部門。ブランド・キャンペーン・媒体費・配信執行・消費者調査・Nielsen syndicated 市場データ。金額は USD 建て。",
        "tables": [f"{C}.marketing_core.{t}" for t in
                   ("brand", "campaign", "media_spend", "consumer_insight",
                    "campaign_execution", "syndicated_market_data")]
                + [f"{C}.marketing_mart.{t}" for t in
                   ("mart_campaign_performance", "mart_brand_market_position",
                    "mart_media_efficiency", "marketing_campaign_performance",
                    "marketing_media_spend", "marketing_consumer_insight")]
                + [f"{C}.sales_core.pos_transaction", f"{C}.master_core.sku",
                   f"{C}.trade_core.promotion_line"],
        # 統治ON で足すもの。横断マートは「誰かが意味を揃えた成果物」なので、
        # 統治前の状態には存在しないものとして扱う（apply_instructions.py が足す）。
        "governed": [f"{C}.xdept_mart.mart_spend_definitions",
                     f"{C}.xdept_mart.mart_brand_investment_return"],
        "samples": [
            "2026年のマーケティング投下額はいくらですか？",
            "ブランド別の投資対効果（ROI）が高い順に教えてください。",
            "計画予算の70%も使えていないキャンペーンを教えてください。",
        ],
    },
    "横断": {
        "title": "Brickshouse 全社横断",
        "description": "Brickshouse Food and Beverage の部門横断。営業（販促を含む）・財務・マーケ・調達を hub キー（account_id / sku_id / brand_id / campaign_id）で貫いた分析。金額の建値が部門で違う（マーケは USD、他は JPY）。",
        "tables": [f"{C}.marketing_mart.marketing_campaign_performance",
                   f"{C}.marketing_mart.marketing_consumer_insight",
                   f"{C}.marketing_core.campaign", f"{C}.marketing_core.consumer_insight",
                   f"{C}.marketing_core.syndicated_market_data",
                   f"{C}.marketing_core.brand", f"{C}.sales_core.pos_transaction",
                   f"{C}.sales_mart.sales_order", f"{C}.finance_mart.finance_ar_invoice",
                   f"{C}.finance_mart.finance_ap_invoice", f"{C}.trade_mart.trade_settlement",
                   f"{C}.procure_mart.procurement_purchase_order",
                   f"{C}.sales_core.order", f"{C}.sales_core.account",
                   f"{C}.finance_core.ar_invoice", f"{C}.trade_core.settlement",
                   f"{C}.procure_core.purchase_order", f"{C}.master_core.sku"],
        "samples": [
            "Brickshouse の2026年の売上はいくらですか？",
            "営業が言う売上と財務が言う売上が違うのはなぜですか？",
            "マーケ投下額と販促費を足して良いですか？",
        ],
        "governed": [f"{C}.xdept_mart.mart_revenue_definitions",
                     f"{C}.xdept_mart.mart_customer_360",
                     f"{C}.xdept_mart.mart_spend_definitions",
                     f"{C}.xdept_mart.mart_brand_investment_return"],
    },
}

# 統治OFF（ベースライン）の instruction。
# 「金額は日本円」とは書かない。マーケが USD 建てであることは統治ONで初めて教える。
# ここに書いてしまうと、通貨の衝突が最初から解決済みになり before/after が測れない。
MINIMAL_INSTRUCTION = (
    "Brickshouse Food and Beverage（ビール類・清涼飲料・健康食品を製造販売する日本の食品飲料メーカー）のデータです。"
    "会計年度は暦年（1月〜12月）。データは 2026-10-24 まで。"
)


def api(method, path, payload=None):
    cmd = ["databricks", "api", method, path, "--profile", PROFILE]
    if payload is not None:
        cmd += ["--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {"_error": (r.stderr or r.stdout).strip()[:400]}
    try:
        return json.loads(r.stdout or "{}")
    except Exception:
        return {"_raw": r.stdout[:400]}


def build(spec):
    b = GenieSpaceBuilder(title=spec["title"], description=spec["description"],
                          warehouse_id=WAREHOUSE)
    for t in spec["tables"]:          # governed は入れない（統治ONで足す）
        # metric view は mart スキーマの非 mart_ 接頭辞のもの
        parts = t.split(".")
        if parts[1].endswith("_mart") and not parts[2].startswith("mart_"):
            b.add_metric_view(t)
        else:
            b.add_table(t)
    b.set_instructions(MINIMAL_INSTRUCTION)
    # サンプル質問はビルダーに API が無いので serialized_space に直接入れる
    sp = b._space
    sp.setdefault("config", {}).setdefault("sample_questions", [])
    for q in spec["samples"]:
        sp["config"]["sample_questions"].append(
            {"id": uuid.uuid4().hex, "question": [q]})
    return b


def main():
    out = {}
    for key, spec in SPACES.items():
        b = build(spec)
        ok = b.validate()
        payload = {
            "title": spec["title"],
            "description": spec["description"],
            "warehouse_id": WAREHOUSE,
            "serialized_space": b.to_json(),
        }
        r = api("post", "/api/2.0/genie/spaces", payload)
        sid = r.get("space_id") or (r.get("space") or {}).get("space_id")
        if sid:
            print(f"  OK  {key:6s} {spec['title']:24s} space_id={sid}  tables={len(spec['tables'])}")
            out[key] = sid
        else:
            print(f"  ERR {key:6s} {str(r)[:300]}")
    if out:
        Path(__file__).with_name("space_ids.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
        print("\n-> 06_genie/space_ids.json")


if __name__ == "__main__":
    main()
