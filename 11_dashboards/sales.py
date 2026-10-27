#!/usr/bin/env python3
"""営業ダッシュボード（販促を含む）。受注と純売上の差が主題。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import (JPY, NUM, PCT, THEME, bar, counter, flt, line, table, text, write)

DS_SALES = {
    "name": "ds_sales",
    "displayName": "受注（月 × 得意先 × チャネル）",
    "queryLines": [
        "SELECT month_start, account_id, account_name, channel, sales_region,\n",
        "       order_status, order_type, order_source,\n",
        "       order_count, order_quantity, order_gross_amount,\n",
        "       order_discount_amount, order_net_amount, backorder_count,\n",
        "       trade_allowance_order_amount,\n",
        "       CASE WHEN channel IN ('SM','CVS','DgS','卸','EC') THEN channel\n",
        "            ELSE '未マップ: ' || channel END AS channel_label,\n",
        "       CASE WHEN channel IN ('SM','CVS','DgS','卸','EC') THEN 0 ELSE 1 END AS is_unmapped_channel\n",
        "FROM sales_mart.mart_sales_performance\n",
    ],
    "columns": [
        {"displayName": "受注純額", "description": "受注の純額（値引後・JPY）。会社の売上ではない",
         "expression": "SUM(`order_net_amount`)"},
        {"displayName": "受注件数", "description": "受注の件数", "expression": "SUM(`order_count`)"},
        {"displayName": "値引率", "description": "値引額 ÷ 受注総額",
         "expression": "SUM(`order_discount_amount`) / NULLIF(SUM(`order_gross_amount`), 0)"},
        {"displayName": "未マップのチャネル行", "description": "マスタに無いチャネルコードの行数（品質シグナル）",
         "expression": "SUM(`is_unmapped_channel`)"},
        {"displayName": "販促対象の受注額", "description": "trade_allowance_order_amount の合計",
         "expression": "SUM(`trade_allowance_order_amount`)"},
    ],
}

DS_REV = {
    "name": "ds_rev",
    "displayName": "「売上」と呼ばれる数字（月次）",
    "queryLines": [
        "SELECT month_start, sales_order_net_amount, invoiced_gross_amount,\n",
        "       trade_discount_amount, deduction_amount, revenue_net_amount,\n",
        "       promo_settlement_net_amount, panel_sellout_amount,\n",
        "       order_to_revenue_gap, revenue_to_order_ratio\n",
        "FROM xdept_mart.mart_revenue_definitions\n",
        "WHERE month_start >= TIMESTAMP'2026-01-01' AND month_start < TIMESTAMP'2026-11-01'\n",
    ],
    "columns": [
        {"displayName": "受注純額（営業）", "description": "sales_core.order の純額。着地見込みに使う",
         "expression": "SUM(`sales_order_net_amount`)"},
        {"displayName": "純売上（財務・正本）", "description": "finance_core.ar_invoice の純額。会社の売上はこれ",
         "expression": "SUM(`revenue_net_amount`)"},
        {"displayName": "受注→純売上 転換率", "description": "純売上 ÷ 受注純額",
         "expression": "SUM(`revenue_net_amount`) / NULLIF(SUM(`sales_order_net_amount`), 0)"},
        {"displayName": "販促値引", "description": "ar_invoice の trade_discount_amount",
         "expression": "SUM(`trade_discount_amount`)"},
        {"displayName": "控除", "description": "ar_invoice の deduction_amount",
         "expression": "SUM(`deduction_amount`)"},
        {"displayName": "販促精算（売上ではない）", "description": "trade_core.settlement の純額。得意先への支払い",
         "expression": "SUM(`promo_settlement_net_amount`)"},
    ],
}

DS_TRADE = {
    "name": "ds_trade",
    "displayName": "販促費の流れ（月次）",
    "queryLines": [
        "SELECT month_start, accrual_amount, claim_amount, settled_amount,\n",
        "       deduction_amount, accrual_to_settlement_gap, settlement_rate\n",
        "FROM trade_mart.mart_trade_spend_flow\n",
        "WHERE month_start IS NOT NULL\n",
    ],
    "columns": [
        {"displayName": "引当", "description": "販促費の引当額（accrual）", "expression": "SUM(`accrual_amount`)"},
        {"displayName": "精算", "description": "実際に支払った額（settlement）", "expression": "SUM(`settled_amount`)"},
        {"displayName": "控除", "description": "得意先が差し引いた額（deduction）", "expression": "SUM(`deduction_amount`)"},
        {"displayName": "精算率", "description": "精算 ÷ 引当",
         "expression": "SUM(`settled_amount`) / NULLIF(SUM(`accrual_amount`), 0)"},
    ],
}

TOP = {
    "name": "ds_top_accounts",
    "displayName": "得意先別の受注と販促",
    "queryLines": [
        "SELECT account_name, channel, sales_region,\n",
        "       SUM(order_net_amount) AS order_net_amount,\n",
        "       SUM(order_count) AS order_count,\n",
        "       SUM(order_discount_amount) / NULLIF(SUM(order_gross_amount), 0) AS discount_rate,\n",
        "       SUM(backorder_count) AS backorder_count\n",
        "FROM sales_mart.mart_sales_performance\n",
        "GROUP BY account_name, channel, sales_region\n",
        "ORDER BY order_net_amount DESC\n",
        "LIMIT 25\n",
    ],
}

HEADER = [
    "# 営業ダッシュボード（販促を含む）\n",
    "\n",
    "**この画面の主題は「受注と売上は違う」こと。** 営業が着地見込みに使う受注純額と、",
    "財務が会社の売上として計上する純売上は、一部出荷・販促値引・控除の分だけ離れます。",
    "左の2つの数字を並べているのはそのためです。\n",
    "\n",
    "期間 2026年1月〜10月（受注は 10/24 まで）・金額は JPY・受注は order_line を持たないヘッダ粒度",
    "（商品軸は店頭実売と配下率で見ます）。出所は `sales_mart.mart_sales_performance` と",
    "`xdept_mart.mart_revenue_definitions`。\n",
]

dash = {
    "datasets": [DS_SALES, DS_REV, DS_TRADE, TOP],
    "pages": [
        {"name": "filters", "displayName": "絞り込み",
         "pageType": "PAGE_TYPE_GLOBAL_FILTERS", "layoutVersion": "GRID_V1",
         "layout": [
             flt("f_channel", "ds_sales", "channel", "チャネル", 0, 0, 4, 2),
             flt("f_region", "ds_sales", "sales_region", "地域", 4, 0, 4, 2),
             flt("f_otype", "ds_sales", "order_type", "受注区分", 8, 0, 4, 2),
         ]},
        {"name": "overview", "displayName": "概況",
         "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1",
         "layout": [
             text("hd", HEADER, 0, 0, 12, 3),
             counter("k_order", "ds_rev", "受注純額（営業）", "受注純額（営業の着地見込み）",
                     "2026年1〜10月・JPY", 0, 3, 4, 3, fmt=JPY),
             counter("k_rev", "ds_rev", "純売上（財務・正本）", "純売上（財務・会社の売上）",
                     "2026年1〜10月・JPY・正本", 4, 3, 4, 3, fmt=JPY),
             counter("k_ratio", "ds_rev", "受注→純売上 転換率", "受注が売上になった割合",
                     "純売上 ÷ 受注純額", 8, 3, 4, 3, fmt=PCT),
             line("l_rev", "ds_rev", "month_start",
                  [{"measure": "受注純額（営業）", "label": "受注純額（営業）"},
                   {"measure": "純売上（財務・正本）", "label": "純売上（財務・正本）"}],
                  "月次：受注純額と純売上（同じ軸で並べる）", 0, 6, 8, 6),
             bar("b_channel", "ds_sales", "channel_label",
                 [{"measure": "受注純額", "label": "受注純額"}],
                 "チャネル別 受注純額（未マップのコードも隠さず出す）", 8, 6, 4, 6, horizontal=True),
             text("hd2", ["## 販促費の流れ — 引当から精算、そして控除へ\n",
                          "販促精算と控除は**売上のマイナス要素**であって売上そのものではありません。",
                          "引当と精算の差が未精算残高です。出所 `trade_mart.mart_trade_spend_flow`。\n"],
                  0, 12, 12, 2),
             line("l_trade", "ds_trade", "month_start",
                  [{"measure": "引当", "label": "引当（accrual）"},
                   {"measure": "精算", "label": "精算（settlement）"},
                   {"measure": "控除", "label": "控除（deduction）"}],
                  "月次：販促費の3段", 0, 14, 8, 5),
             counter("k_settle", "ds_trade", "精算率", "引当のうち精算された割合",
                     "精算 ÷ 引当", 8, 14, 4, 3, fmt=PCT),
             counter("k_unmapped", "ds_sales", "未マップのチャネル行",
                     "マスタに無いチャネルコードの行数", "品質シグナル・件数", 8, 17, 4, 2, fmt=NUM),
             text("hd3", ["## 得意先別（受注純額の上位25社）\n"], 0, 19, 12, 1),
             table("t_top", "ds_top_accounts", [
                 {"field": "account_name", "label": "得意先"},
                 {"field": "channel", "label": "チャネル"},
                 {"field": "sales_region", "label": "地域"},
                 {"field": "order_net_amount", "label": "受注純額", "format": JPY},
                 {"field": "order_count", "label": "受注件数", "format": NUM},
                 {"field": "discount_rate", "label": "値引率", "format": PCT},
                 {"field": "backorder_count", "label": "取り寄せ件数", "format": NUM},
             ], "得意先別 受注（上位25社）", 0, 20, 12, 7),
         ]},
    ],
    "uiSettings": {"theme": THEME},
}

if __name__ == "__main__":
    write("sales", dash)
