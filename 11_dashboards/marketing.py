#!/usr/bin/env python3
"""
マーケダッシュボード。主題は2つ。
  1. 投下額・調査費・媒体費は別物（ECM の metric view が同名の measure を持つ）
  2. 金額は USD 建てで、他部門の JPY とは足せない
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import (JPY, NUM, PCT, THEME, USD, bar, counter, flt, line, table, text, write)

DS_CAMPAIGN = {
    "name": "ds_campaign",
    "displayName": "キャンペーン（USD建て）",
    "queryLines": [
        "SELECT campaign_id, campaign_code, campaign_name, campaign_type, channel,\n",
        "       objective, brand_id, brand_name, brand_category, owner_division,\n",
        "       start_date, end_date, campaign_status, currency_code,\n",
        "       planned_budget_usd, actual_spend_usd, media_actual_usd,\n",
        "       agency_fee_usd, execution_count, underspent_executions,\n",
        "       total_impressions, clicks_delivered, burn_rate, cpm_usd\n",
        "FROM marketing_mart.mart_campaign_performance\n",
    ],
    "columns": [
        {"displayName": "投下額 USD", "description": "キャンペーンの実投下額。これが「マーケ投下額」の正本",
         "expression": "SUM(`actual_spend_usd`)"},
        {"displayName": "計画予算 USD", "description": "planned_budget_usd の合計。実績ではない",
         "expression": "SUM(`planned_budget_usd`)"},
        {"displayName": "媒体費 USD", "description": "投下額のうち媒体購入分。投下額の全部ではない",
         "expression": "SUM(`media_actual_usd`)"},
        {"displayName": "消化率", "description": "投下額 ÷ 計画予算",
         "expression": "SUM(`actual_spend_usd`) / NULLIF(SUM(`planned_budget_usd`), 0)"},
        {"displayName": "キャンペーン数", "description": "件数", "expression": "COUNT(`campaign_id`)"},
        {"displayName": "未消化の執行数", "description": "計画の70%未満しか使えていない執行の数",
         "expression": "SUM(`underspent_executions`)"},
        {"displayName": "CPM USD", "description": "千インプレッションあたり費用",
         "expression": "1000.0 * SUM(`actual_spend_usd`) / NULLIF(SUM(`total_impressions`), 0)"},
    ],
}

DS_SPEND = {
    "name": "ds_spend",
    "displayName": "「マーケに使ったお金」と呼ばれる数字（月次）",
    "queryLines": [
        "SELECT month_start, campaign_actual_usd, media_actual_usd,\n",
        "       execution_actual_usd, consumer_insight_usd, trade_settled_jpy,\n",
        "       insight_to_campaign_ratio, campaign_burn_rate\n",
        "FROM xdept_mart.mart_spend_definitions\n",
        "WHERE month_start >= TIMESTAMP'2026-01-01' AND month_start < TIMESTAMP'2026-11-01'\n",
    ],
    "columns": [
        {"displayName": "キャンペーン投下 USD", "description": "正本。marketing.campaign の実投下額",
         "expression": "SUM(`campaign_actual_usd`)"},
        {"displayName": "媒体費 USD（内訳）", "description": "投下額のうち媒体分",
         "expression": "SUM(`media_actual_usd`)"},
        {"displayName": "消費者調査費 USD", "description": "調査会社に払った費用。投下額ではない",
         "expression": "SUM(`consumer_insight_usd`)"},
        {"displayName": "販促精算 JPY", "description": "営業部門の販促。**建値が違うので上の USD と足せない**",
         "expression": "SUM(`trade_settled_jpy`)"},
        {"displayName": "調査費 ÷ 投下額", "description": "取り違えたときの倍率の逆数",
         "expression": "SUM(`consumer_insight_usd`) / NULLIF(SUM(`campaign_actual_usd`), 0)"},
    ],
}

DS_BRAND = {
    "name": "ds_brand",
    "displayName": "ブランド別の投資対効果と市場シェア",
    "queryLines": [
        "SELECT brand_name, brand_category, owner_division, lifecycle_status,\n",
        "       campaign_actual_usd, campaign_actual_jpy, trade_funding_jpy,\n",
        "       total_investment_jpy, brand_sales_jpy, return_on_investment,\n",
        "       roi_on_panel_basis, avg_dollar_share_pct, market_dollar_sales_usd,\n",
        "       awareness_pct, nps_score, marketing_spend_fx_rate\n",
        "FROM xdept_mart.mart_brand_investment_return\n",
        "ORDER BY return_on_investment DESC\n",
    ],
    "columns": [
        {"displayName": "ブランド売上 JPY（推計）",
         "description": "市場全体 × 自社シェア を JPY 換算した推計。財務の純売上とは一致しない",
         "expression": "SUM(`brand_sales_jpy`)"},
        {"displayName": "総投資 JPY", "description": "マーケ投下(USD×150) + 販促費(JPY)",
         "expression": "SUM(`total_investment_jpy`)"},
        {"displayName": "ROI", "description": "ブランド売上(推計) ÷ 総投資。ブランド間の相対比較に使う",
         "expression": "SUM(`brand_sales_jpy`) / NULLIF(SUM(`total_investment_jpy`), 0)"},
        {"displayName": "平均シェア", "description": "Nielsen syndicated の金額シェア",
         "expression": "AVG(`avg_dollar_share_pct`) / 100.0"},
    ],
}

DS_MEDIA = {
    "name": "ds_media",
    "displayName": "媒体チャネル別の効率（USD建て）",
    "queryLines": [
        "SELECT month_start, media_channel, media_type, buying_type,\n",
        "       planned_spend_usd, actual_spend_usd, agency_fee_usd,\n",
        "       impressions, clicks, reach, line_count, missing_currency_rows,\n",
        "       working_media_usd, cpm_usd, cpc_usd, ctr_pct, avg_roi_index, burn_rate\n",
        "FROM marketing_mart.mart_media_efficiency\n",
    ],
    "columns": [
        {"displayName": "媒体投下 USD", "description": "媒体購入の実額", "expression": "SUM(`actual_spend_usd`)"},
        {"displayName": "媒体CPM USD", "description": "千インプレッションあたり費用",
         "expression": "1000.0 * SUM(`actual_spend_usd`) / NULLIF(SUM(`impressions`), 0)"},
        {"displayName": "ワーキングメディア比率", "description": "枠に出た分 ÷ 媒体投下額",
         "expression": "SUM(`working_media_usd`) / NULLIF(SUM(`actual_spend_usd`), 0)"},
        {"displayName": "通貨が欠けた明細", "description": "currency_code が空の行数。集計前に必ず見る",
         "expression": "SUM(`missing_currency_rows`)"},
    ],
}

HEADER = [
    "# マーケティングダッシュボード\n",
    "\n",
    "**この部門の金額はすべて USD 建てです。** 営業・財務・販促は JPY なので、",
    "換算せずに足したり割ったりはできません（換算すると150倍ずれます）。",
    "換算が必要な集計は `xdept_mart.mart_brand_investment_return` を使い、",
    "レートと根拠を表の中に持たせています。\n",
    "\n",
    "**もう1つの注意**: 「マーケ投下額」はキャンペーン投下額です。",
    "消費者調査費は同じ名前の measure を持ちますが投下額ではなく、約18分の1の規模です。",
    "媒体費は投下額の一部（約7割）で、全部ではありません。\n",
    "\n",
    "期間 2026年1月〜10月・出所は `marketing_mart.mart_campaign_performance` /",
    "`mart_media_efficiency` と `xdept_mart.mart_spend_definitions` / `mart_brand_investment_return`。\n",
]

dash = {
    "datasets": [DS_CAMPAIGN, DS_SPEND, DS_BRAND, DS_MEDIA],
    "pages": [
        {"name": "filters", "displayName": "絞り込み",
         "pageType": "PAGE_TYPE_GLOBAL_FILTERS", "layoutVersion": "GRID_V1",
         "layout": [
             flt("f_cat", "ds_campaign", "brand_category", "カテゴリ", 0, 0, 4, 2),
             flt("f_type", "ds_campaign", "campaign_type", "キャンペーン種別", 4, 0, 4, 2),
             flt("f_status", "ds_campaign", "campaign_status", "ステータス", 8, 0, 4, 2),
         ]},
        {"name": "overview", "displayName": "概況",
         "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1",
         "layout": [
             text("hd", HEADER, 0, 0, 12, 4),
             counter("k_spend", "ds_campaign", "投下額 USD", "マーケ投下額（正本）",
                     "2026年1〜10月・**USD**", 0, 4, 4, 3, fmt=USD),
             counter("k_burn", "ds_campaign", "消化率", "計画予算の消化率",
                     "投下額 ÷ 計画予算", 4, 4, 4, 3, fmt=PCT),
             counter("k_cpm", "ds_campaign", "CPM USD", "CPM（千インプレッションあたり）",
                     "投下額 ÷ インプレッション・USD", 8, 4, 4, 3, fmt=USD),
             text("hd2", ["## 「マーケに使ったお金」と呼ばれる4つの数字\n",
                          "投下額・媒体費・調査費は **USD**、販促精算は **JPY**。",
                          "列名の接尾辞が建値です。**合計列は意図的に置いていません**。\n"],
                  0, 7, 12, 2),
             line("l_spend", "ds_spend", "month_start",
                  [{"measure": "キャンペーン投下 USD", "label": "キャンペーン投下（USD・正本）"},
                   {"measure": "媒体費 USD（内訳）", "label": "媒体費（USD・内訳）"},
                   {"measure": "消費者調査費 USD", "label": "消費者調査費（USD・投下ではない）"}],
                  "月次：USD建ての3つ（同じ軸で並べてよい）", 0, 9, 8, 6),
             counter("k_insight", "ds_spend", "消費者調査費 USD", "消費者調査費（投下額ではない）",
                     "投下額の約5%・USD", 8, 9, 4, 3, fmt=USD),
             counter("k_trade_jpy", "ds_spend", "販促精算 JPY", "販促精算（JPY・足せない）",
                     "建値が違うので上の USD と合算不可", 8, 12, 4, 3, fmt=JPY),
             text("hd3", ["## ブランド別の投資対効果 — 市場が大きくてもシェアが薄ければ戻らない\n",
                          "ROI の分子は **市場全体 × 自社シェア の JPY 換算推計**（CPG の実務標準）。",
                          "受注がヘッダ粒度で財務の純売上をブランドに割れないためで、",
                          "全社 P/L の粗利とは一致しません。用途はブランド間の相対比較です。\n"],
                  0, 15, 12, 2),
             bar("b_roi", "ds_brand", "brand_name",
                 [{"measure": "ROI", "label": "ROI（売上推計 ÷ 総投資）"}],
                 "ブランド別 ROI（高い順）", 0, 17, 6, 6, horizontal=True),
             bar("b_share", "ds_brand", "brand_name",
                 [{"measure": "平均シェア", "label": "市場シェア"}],
                 "ブランド別 市場シェア（Nielsen syndicated）", 6, 17, 6, 6, horizontal=True),
             text("hd4", ["## 媒体の効率と、集計の信頼度\n",
                          "`missing_currency_rows` は **通貨が記録されていない明細の数**。",
                          "空を JPY と思って集計すると静かに間違うので、集計前にここを見ます。\n"],
                  0, 23, 12, 2),
             bar("b_cpm", "ds_media", "media_channel",
                 [{"measure": "媒体CPM USD", "label": "CPM（USD）"}],
                 "媒体チャネル別 CPM（安い順に読む）", 0, 25, 6, 5),
             counter("k_missing", "ds_media", "通貨が欠けた明細", "通貨が記録されていない明細",
                     "品質シグナル・件数", 6, 25, 3, 3, fmt=NUM),
             counter("k_working", "ds_media", "ワーキングメディア比率", "ワーキングメディア比率",
                     "枠に出た分 ÷ 媒体投下額", 9, 25, 3, 3, fmt=PCT),
             table("t_brand", "ds_brand", [
                 {"field": "brand_name", "label": "ブランド"},
                 {"field": "brand_category", "label": "カテゴリ"},
                 {"field": "market_dollar_sales_usd", "label": "市場規模（USD）", "format": USD},
                 {"field": "avg_dollar_share_pct", "label": "シェア(%)", "format": NUM},
                 {"field": "brand_sales_jpy", "label": "ブランド売上（推計JPY）", "format": JPY},
                 {"field": "total_investment_jpy", "label": "総投資（JPY）", "format": JPY},
                 {"field": "return_on_investment", "label": "ROI", "format": NUM},
                 {"field": "roi_on_panel_basis", "label": "ROI(POS基準・検算用)", "format": NUM},
             ], "ブランド別 明細（ROI 高い順）", 0, 30, 12, 6),
         ]},
    ],
    "uiSettings": {"theme": THEME},
}

if __name__ == "__main__":
    write("marketing", dash)
