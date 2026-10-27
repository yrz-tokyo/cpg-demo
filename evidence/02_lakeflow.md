# 02 Lakeflow（bronze → silver → gold）

pipeline_id = 5824de8f-e369-47f9-8844-abd16c5892f7 / serverless / photon
bronze 24 STREAMING TABLE / silver 24 MATERIALIZED VIEW / gold 8 MATERIALIZED VIEW
silver は PK 24・FK 53・expectations 25 をパイプライン定義で宣言

### 層別オブジェクト数と行数
```
table_schema | table_type | objects
finance_core | MATERIALIZED_VIEW | 6
finance_mart | MATERIALIZED_VIEW | 2
finance_mart | METRIC_VIEW | 2
master_core | MATERIALIZED_VIEW | 3
master_mart | METRIC_VIEW | 1
ops_landing | MANAGED | 1
ops_landing | STREAMING_TABLE | 24
procure_core | MATERIALIZED_VIEW | 2
procure_mart | METRIC_VIEW | 1
sales_core | MATERIALIZED_VIEW | 7
sales_mart | MATERIALIZED_VIEW | 2
sales_mart | METRIC_VIEW | 4
trade_core | MATERIALIZED_VIEW | 6
trade_mart | MATERIALIZED_VIEW | 2
trade_mart | METRIC_VIEW | 5
xdept_mart | MATERIALIZED_VIEW | 2
```

### フロー別 出力行数
```
rongzi_catalog_dev.sales_core.invoice             22,000
rongzi_catalog_dev.sales_mart.mart_sales_performance    15,400
rongzi_catalog_dev.finance_mart.mart_revenue_reconciliation     4,241
rongzi_catalog_dev.trade_core.promotion_line       4,000
rongzi_catalog_dev.trade_core.accrual              4,000
rongzi_catalog_dev.sales_core.distribution_point     2,400
rongzi_catalog_dev.sales_mart.mart_account_coverage     2,396
rongzi_catalog_dev.trade_mart.mart_promotion_roi       400
rongzi_catalog_dev.trade_core.promotion_event        400
rongzi_catalog_dev.finance_mart.mart_standard_cost_compare       298
rongzi_catalog_dev.xdept_mart.mart_customer_360       149
rongzi_catalog_dev.procure_core.supplier              80
rongzi_catalog_dev.finance_core.gl_account            60
rongzi_catalog_dev.sales_core.rep                     60
rongzi_catalog_dev.finance_core.cost_center           40
rongzi_catalog_dev.trade_core.fund                    30
rongzi_catalog_dev.master_core.category               24
rongzi_catalog_dev.finance_core.profit_center         20
rongzi_catalog_dev.sales_core.territory               12
rongzi_catalog_dev.xdept_mart.mart_revenue_definitions        11
rongzi_catalog_dev.trade_mart.mart_trade_spend_flow        10
```

### expectations 結果（イベントログより・合格/不合格レコード数）
```
mart_revenue_definitions     ex_month_present           pass=11 fail=0
mart_revenue_reconciliation  ex_recon_closes            pass=3995 fail=246
```

### expectations の効果（bronze → silver で落ちた行）
```
tbl | bronze_rows | silver_rows | dropped | dropped_pct
sales_core.pos_transaction | 80000 | 79360 | 640 | 0.8
sales_core.order | 24000 | 23523 | 477 | 1.99
finance_core.ar_invoice | 22000 | 21847 | 153 | 0.7
finance_core.ap_invoice | 8000 | 7952 | 48 | 0.6
procure_core.purchase_order | 8000 | 7952 | 48 | 0.6
trade_core.deduction | 5000 | 4965 | 35 | 0.7
trade_core.settlement | 1800 | 1782 | 18 | 1.0
master_core.product_standard_cost | 300 | 298 | 2 | 0.67
master_core.sku | 300 | 298 | 2 | 0.67
sales_core.account | 150 | 149 | 1 | 0.67
```
