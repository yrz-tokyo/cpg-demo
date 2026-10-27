# 04 定義衝突（業界データモデルに素で存在する）

ECM の metric view は `total_net_amount` / `total_gross_amount` という
完全同名の measure を sales / finance / trade / procurement の4ドメインに持つ。
うち2つ（ap_invoice, purchase_order）は売上ですらない。衝突は仕込みではない。

- `sales_mart.sales_order.total_net_amount` = 1555.5 億円  — 受注（営業）
- `finance_mart.finance_ar_invoice.total_net_amount` = 1270.2 億円  — 純売上（財務）★正本
- `trade_mart.trade_settlement.total_net_amount` = 106.4 億円  — 販促精算（販促・売上でない）
- `finance_mart.finance_ap_invoice.total_net_amount` = 529.4 億円  — 買掛（財務・売上でない）
- `procure_mart.procurement_purchase_order.total_net_amount` = 597.1 億円  — 発注（調達・売上でない）

### xdept_mart.mart_revenue_definitions（月次で5つの数字を並べた横断マート）
```
mo | order_net | invoiced | revenue_net | promo_settle | payable | po | panel | revenue_to_order_ratio
2026-01 | 157.8 | 93.3 | 87.8 | 10.8 | 54.7 | 62.4 | 3.4 | 0.5564
2026-02 | 124.2 | 118.2 | 111.2 | 10.4 | 48.0 | 55.8 | 2.6 | 0.8954
2026-03 | 139.5 | 127.2 | 120.1 | 10.8 | 58.3 | 62.8 | 3.0 | 0.8605
2026-04 | 142.9 | 110.8 | 104.3 | 12.5 | 53.5 | 63.2 | 2.9 | 0.7301
2026-05 | 144.9 | 120.6 | 113.9 | 10.1 | 53.1 | 59.9 | 3.3 | 0.7862
2026-06 | 165.4 | 131.2 | 123.7 | 10.1 | 51.3 | 63.3 | 3.4 | 0.7478
2026-07 | 182.3 | 155.9 | 146.7 | 9.9 | 53.9 | 60.8 | 4.1 | 0.8044
2026-08 | 194.2 | 165.9 | 156.6 | 12.7 | 55.8 | 59.4 | 3.8 | 0.8060
2026-09 | 176.9 | 163.9 | 154.4 | 11.7 | 56.1 | 61.2 | 3.6 | 0.8729
2026-10 | 127.3 | 142.4 | 134.1 | 7.3 | 44.8 | 48.3 | 2.6 | 1.0534
2026-11 |  | 18.5 | 17.4 |  |  |  |  | 
```
