#!/usr/bin/env python3
"""財務ダッシュボード。純売上の正本と、そこへ至る各段の目減りが主題。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import (JPY, NUM, PCT, THEME, bar, counter, flt, line, table, text, write)

DS_RECON = {
    "name": "ds_recon",
    "displayName": "売上照合（月 × 得意先 × チャネル）",
    "queryLines": [
        "SELECT month_start, account_id, account_name, channel, invoice_status,\n",
        "       invoice_count, invoiced_gross_amount, trade_discount_amount,\n",
        "       deduction_amount, revenue_net_amount, tax_amount,\n",
        "       payment_amount, open_receivable_amount, short_payment_amount\n",
        "FROM finance_mart.mart_revenue_reconciliation\n",
    ],
    "columns": [
        {"displayName": "純売上", "description": "請求総額 − 販促値引 − 控除。会社の売上の正本",
         "expression": "SUM(`revenue_net_amount`)"},
        {"displayName": "請求総額", "description": "ar_invoice の gross_amount",
         "expression": "SUM(`invoiced_gross_amount`)"},
        {"displayName": "販促値引", "description": "ar_invoice の trade_discount_amount",
         "expression": "SUM(`trade_discount_amount`)"},
        {"displayName": "控除", "description": "ar_invoice の deduction_amount",
         "expression": "SUM(`deduction_amount`)"},
        {"displayName": "リーケージ", "description": "販促値引 + 控除。請求したのに売上にならなかった額",
         "expression": "SUM(`trade_discount_amount`) + SUM(`deduction_amount`)"},
        {"displayName": "リーケージ率", "description": "リーケージ ÷ 請求総額",
         "expression": "(SUM(`trade_discount_amount`) + SUM(`deduction_amount`)) / NULLIF(SUM(`invoiced_gross_amount`), 0)"},
        {"displayName": "未回収売掛", "description": "open_receivable_amount の合計。リーケージとは別物",
         "expression": "SUM(`open_receivable_amount`)"},
        {"displayName": "入金額", "description": "payment_amount の合計", "expression": "SUM(`payment_amount`)"},
    ],
}

DS_RATE = {
    "name": "ds_rate",
    "displayName": "原価率（月次）",
    "queryLines": [
        "SELECT month_start, revenue_net_amount, purchase_order_net_amount,\n",
        "       payable_net_amount, sales_order_net_amount\n",
        "FROM xdept_mart.mart_revenue_definitions\n",
        "WHERE month_start >= TIMESTAMP'2026-01-01' AND month_start < TIMESTAMP'2026-11-01'\n",
    ],
    "columns": [
        {"displayName": "原価率", "description": "発注(purchase_order) ÷ 純売上。買掛や受注を分子にしてはならない",
         "expression": "SUM(`purchase_order_net_amount`) / NULLIF(SUM(`revenue_net_amount`), 0)"},
        {"displayName": "発注額（仕入）", "description": "procurement.purchase_order の純額。売上ではない",
         "expression": "SUM(`purchase_order_net_amount`)"},
        {"displayName": "買掛額（仕入）", "description": "finance.ap_invoice の純額。売上ではない",
         "expression": "SUM(`payable_net_amount`)"},
    ],
}

DS_COST = {
    "name": "ds_cost",
    "displayName": "標準原価の2系統比較",
    "queryLines": [
        "SELECT sku_id, product_name, product_line,\n",
        "       product_side_unit_cost, finance_side_unit_cost,\n",
        "       unit_cost_gap, unit_cost_gap_ratio\n",
        "FROM finance_mart.mart_standard_cost_compare\n",
        "WHERE unit_cost_gap_ratio IS NOT NULL\n",
        "ORDER BY abs(unit_cost_gap_ratio) DESC\n",
        "LIMIT 25\n",
    ],
}

DS_DISPUTE = {
    "name": "ds_dispute",
    "displayName": "係争中・照合不一致（件数と金額）",
    "queryLines": [
        "SELECT '係争中の売掛請求' AS kind, count(*) AS cnt, sum(net_amount) AS amount\n",
        "FROM finance_core.ar_invoice WHERE dispute_status = 'open'\n",
        "UNION ALL\n",
        "SELECT '照合不一致の買掛請求', count(*), sum(net_amount)\n",
        "FROM finance_core.ap_invoice WHERE match_status <> 'matched'\n",
        "UNION ALL\n",
        "SELECT '係争中の控除', count(*), sum(net_amount)\n",
        "FROM trade_core.deduction WHERE deduction_status = 'disputed'\n",
    ],
}

HEADER = [
    "# 財務ダッシュボード\n",
    "\n",
    "**この画面の数字が会社の売上の正本です。** 純売上 = 請求総額 − 販促値引 − 控除。",
    "受注(営業)・発注(調達)・買掛(財務)・販促精算(販促) は同じ `total_net_amount` という名前の",
    "指標を持ちますが、売上ではありません。\n",
    "\n",
    "期間 2026年1月〜10月・金額は JPY・原価率は 発注 ÷ 純売上。",
    "出所は `finance_mart.mart_revenue_reconciliation`（得意先×月）と",
    "`xdept_mart.mart_revenue_definitions`（月）。\n",
]

dash = {
    "datasets": [DS_RECON, DS_RATE, DS_COST, DS_DISPUTE],
    "pages": [
        {"name": "filters", "displayName": "絞り込み",
         "pageType": "PAGE_TYPE_GLOBAL_FILTERS", "layoutVersion": "GRID_V1",
         "layout": [
             flt("f_channel", "ds_recon", "channel", "チャネル", 0, 0, 6, 2),
             flt("f_status", "ds_recon", "invoice_status", "請求ステータス", 6, 0, 6, 2),
         ]},
        {"name": "overview", "displayName": "概況",
         "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1",
         "layout": [
             text("hd", HEADER, 0, 0, 12, 3),
             counter("k_rev", "ds_recon", "純売上", "純売上（会社の売上・正本）",
                     "2026年1〜10月・JPY", 0, 3, 4, 3, fmt=JPY),
             counter("k_leak", "ds_recon", "リーケージ率", "請求したのに売上にならなかった割合",
                     "(販促値引+控除) ÷ 請求総額", 4, 3, 4, 3, fmt=PCT),
             counter("k_cogs", "ds_rate", "原価率", "原価率",
                     "発注 ÷ 純売上（買掛・受注は分子に使わない）", 8, 3, 4, 3, fmt=PCT),
             line("l_steps", "ds_recon", "month_start",
                  [{"measure": "請求総額", "label": "請求総額"},
                   {"measure": "純売上", "label": "純売上（正本）"},
                   {"measure": "入金額", "label": "入金額"}],
                  "月次：請求総額 → 純売上 → 入金", 0, 6, 8, 6),
             counter("k_open", "ds_recon", "未回収売掛", "未回収売掛残高",
                     "リーケージとは別物・JPY", 8, 6, 4, 3, fmt=JPY),
             counter("k_leak_amt", "ds_recon", "リーケージ", "リーケージ額",
                     "販促値引 + 控除・JPY", 8, 9, 4, 3, fmt=JPY),
             text("hd2", ["## 目減りの内訳と、チャネル別の構成\n",
                          "販促値引と控除がどのチャネルで出ているか。**未回収売掛（入金が無い）と",
                          "リーケージ（そもそも売上にならなかった）は別物**です。\n"],
                  0, 12, 12, 2),
             bar("b_leak", "ds_recon", "channel",
                 [{"measure": "販促値引", "label": "販促値引"},
                  {"measure": "控除", "label": "控除"}],
                 "チャネル別 リーケージの内訳", 0, 14, 6, 5),
             bar("b_rev", "ds_recon", "channel",
                 [{"measure": "純売上", "label": "純売上"}],
                 "チャネル別 純売上", 6, 14, 6, 5, horizontal=True),
             text("hd3", ["## 止まっている伝票 — 係争中と照合不一致\n",
                          "判定列を取り違えやすいところ。係争中の売掛は `dispute_status='open'`、",
                          "照合不一致の買掛は `match_status<>'matched'`、係争中の控除は",
                          "`deduction_status='disputed'`。\n"],
                  0, 19, 12, 2),
             table("t_dispute", "ds_dispute", [
                 {"field": "kind", "label": "種類"},
                 {"field": "cnt", "label": "件数", "format": NUM},
                 {"field": "amount", "label": "金額", "format": JPY},
             ], "係争中・照合不一致の件数と金額", 0, 21, 5, 4),
             table("t_cost", "ds_cost", [
                 {"field": "sku_id", "label": "SKU ID"},
                 {"field": "product_name", "label": "商品"},
                 {"field": "product_line", "label": "製品ライン"},
                 {"field": "product_side_unit_cost", "label": "製品側 単位原価", "format": JPY},
                 {"field": "finance_side_unit_cost", "label": "財務側 単位原価", "format": JPY},
                 {"field": "unit_cost_gap_ratio", "label": "乖離率", "format": PCT},
             ], "標準原価が2系統で食い違っている SKU（乖離の大きい順25件）", 5, 21, 7, 4),
         ]},
    ],
    "uiSettings": {"theme": THEME},
}

if __name__ == "__main__":
    write("finance", dash)
