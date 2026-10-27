-- 自動生成: 01_model/extract_model.py (extract_metric_views)
-- ECM の metric view を素のまま移植。source の3部名のみ差し替える。
-- 採用 16 本 / source がフェーズ外で落としたもの 15 本

-- source: ECM _metrics.customer_account_overview  (over customer.account)  -> sales_mart.customer_account_overview
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`sales_mart`.`customer_account_overview`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "High‑level customer account KPIs for executive and operational insight."
  source: "`rongzi_catalog_dev`.`sales_core`.`account`"
  dimensions:
    - name: "market_segment"
      expr: market_segment
      comment: "Segment of the market the account belongs to."
    - name: "account_status"
      expr: account_status
      comment: "Current status of the account (e.g., Active, Inactive)."
    - name: "channel"
      expr: channel
      comment: "Sales channel through which the account is served."
    - name: "key_account_flag"
      expr: key_account_flag
      comment: "Flag indicating a key strategic account (True/False)."
    - name: "month_created"
      expr: DATE_TRUNC('month', created_timestamp)
      comment: "Month the account record was created."
  measures:
    - name: "total_accounts"
      expr: COUNT(1)
      comment: "Total number of accounts."
    - name: "key_account_count"
      expr: SUM(CASE WHEN key_account_flag THEN 1 ELSE 0 END)
      comment: "Number of key strategic accounts."
    - name: "active_account_count"
      expr: SUM(CASE WHEN account_status = 'Active' THEN 1 ELSE 0 END)
      comment: "Count of accounts with status 'Active'."
    - name: "avg_days_since_first_order"
      expr: AVG(DATEDIFF(current_date(), first_order_date))
      comment: "Average number of days since the first order for each account."
$$;

-- source: ECM _metrics.finance_ap_invoice  (over finance.ap_invoice)  -> finance_mart.finance_ap_invoice
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`finance_mart`.`finance_ap_invoice`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Key AP invoice financial metrics for payable analysis"
  source: "`rongzi_catalog_dev`.`finance_core`.`ap_invoice`"
  dimensions:
    - name: "fiscal_year"
      expr: fiscal_year
      comment: "Fiscal year of the invoice"
    - name: "company_code_id"
      expr: company_code_id
      comment: "Company code identifier"
    - name: "supplier_id"
      expr: supplier_id
      comment: "Supplier identifier"
    - name: "currency_code"
      expr: currency_code
      comment: "Currency of the invoice"
    - name: "invoice_status"
      expr: invoice_status
      comment: "Current status of the invoice"
    - name: "posting_month"
      expr: DATE_TRUNC('month', posting_date)
      comment: "Month of posting date"
  measures:
    - name: "total_gross_amount"
      expr: SUM(CAST(gross_amount AS DOUBLE))
      comment: "Total gross amount of AP invoices"
    - name: "total_net_amount"
      expr: SUM(CAST(net_amount AS DOUBLE))
      comment: "Total net amount after discounts and taxes"
    - name: "total_tax_amount"
      expr: SUM(CAST(tax_amount AS DOUBLE))
      comment: "Total tax amount collected"
    - name: "average_payment_delay_days"
      expr: AVG(CAST(DATEDIFF(payment_date, invoice_date) AS DOUBLE))
      comment: "Average days between invoice date and payment date"
    - name: "average_discount_rate_pct"
      expr: AVG(100.0 * discount_amount / NULLIF(gross_amount,0))
      comment: "Average discount rate as percentage of gross amount"
$$;

-- source: ECM _metrics.finance_ar_invoice  (over finance.ar_invoice)  -> finance_mart.finance_ar_invoice
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`finance_mart`.`finance_ar_invoice`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "AR invoice performance metrics for receivable management"
  source: "`rongzi_catalog_dev`.`finance_core`.`ar_invoice`"
  dimensions:
    - name: "company_code_id"
      expr: company_code_id
      comment: "Company code identifier"
    - name: "profit_center_id"
      expr: profit_center_id
      comment: "Profit center responsible for the sale"
    - name: "sales_org_code"
      expr: sales_org_code
      comment: "Sales organization code"
    - name: "currency_code"
      expr: currency_code
      comment: "Currency of the invoice"
    - name: "invoice_status"
      expr: invoice_status
      comment: "Current status of the invoice"
  measures:
    - name: "total_gross_amount"
      expr: SUM(CAST(gross_amount AS DOUBLE))
      comment: "Total gross amount of AR invoices"
    - name: "total_net_amount"
      expr: SUM(CAST(net_amount AS DOUBLE))
      comment: "Total net amount after deductions and taxes"
    - name: "total_open_amount"
      expr: SUM(CAST(open_amount AS DOUBLE))
      comment: "Total open (unpaid) amount"
    - name: "average_collection_delay_days"
      expr: AVG(CAST(DATEDIFF(payment_date, invoice_date) AS DOUBLE))
      comment: "Average days between invoice date and payment receipt"
    - name: "average_collection_rate_pct"
      expr: AVG(100.0 * payment_amount / NULLIF(gross_amount,0))
      comment: "Average collection rate as percentage of gross amount"
$$;

-- source: ECM _metrics.marketing_campaign_performance  (over marketing.campaign)  -> marketing_mart.marketing_campaign_performance
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`marketing_mart`.`marketing_campaign_performance`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Key financial performance indicators for marketing campaigns"
  source: "`rongzi_catalog_dev`.`marketing_core`.`campaign`"
  dimensions:
    - name: "campaign_id"
      expr: campaign_id
      comment: "Unique identifier of the campaign"
    - name: "brand_id"
      expr: brand_id
      comment: "Brand associated with the campaign"
    - name: "campaign_name"
      expr: campaign_name
      comment: "Descriptive name of the campaign"
    - name: "campaign_type"
      expr: campaign_type
      comment: "Type of campaign (e.g., digital, TV, print)"
    - name: "channel"
      expr: channel
      comment: "Primary media channel used"
    - name: "start_date"
      expr: start_date
      comment: "Campaign start date"
    - name: "end_date"
      expr: end_date
      comment: "Campaign end date"
    - name: "fiscal_year"
      expr: fiscal_year
      comment: "Fiscal year of the campaign"
    - name: "campaign_status"
      expr: campaign_status
      comment: "Current status of the campaign"
  measures:
    - name: "campaign_count"
      expr: COUNT(1)
      comment: "Number of campaigns in the selected scope"
    - name: "total_actual_spend_usd"
      expr: SUM(CAST(actual_spend_usd AS DOUBLE))
      comment: "Total actual spend in USD for the campaign"
    - name: "total_planned_budget_usd"
      expr: SUM(CAST(planned_budget_usd AS DOUBLE))
      comment: "Total planned budget in USD for the campaign"
    - name: "spend_vs_budget_pct"
      expr: ROUND(100.0 * SUM(CAST(actual_spend_usd AS DOUBLE)) / NULLIF(SUM(CAST(planned_budget_usd AS DOUBLE)), 0), 2)
      comment: "Actual spend as a percentage of planned budget"
$$;

-- source: ECM _metrics.marketing_media_spend  (over marketing.media_spend)  -> marketing_mart.marketing_media_spend
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`marketing_mart`.`marketing_media_spend`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Financial efficiency and reach metrics for media spend"
  source: "`rongzi_catalog_dev`.`marketing_core`.`media_spend`"
  dimensions:
    - name: "brand_id"
      expr: brand_id
      comment: "Brand associated with the spend"
    - name: "campaign_id"
      expr: campaign_id
      comment: "Campaign identifier"
    - name: "market_id"
      expr: market_id
      comment: "Market identifier"
    - name: "media_channel"
      expr: media_channel
      comment: "Media channel (e.g., TV, Digital)"
    - name: "media_type"
      expr: media_type
      comment: "Media type (e.g., Video, Display)"
    - name: "spend_date"
      expr: spend_date
      comment: "Date of the spend"
  measures:
    - name: "spend_record_count"
      expr: COUNT(1)
      comment: "Number of media spend records"
    - name: "total_actual_spend_amount"
      expr: SUM(CAST(actual_spend_amount AS DOUBLE))
      comment: "Total actual media spend amount"
    - name: "total_impressions"
      expr: SUM(CAST(impressions AS DOUBLE))
      comment: "Total impressions delivered"
    - name: "total_clicks"
      expr: SUM(CAST(clicks AS DOUBLE))
      comment: "Total clicks generated"
    - name: "cpm"
      expr: ROUND(1000.0 * SUM(CAST(actual_spend_amount AS DOUBLE)) / NULLIF(SUM(CAST(impressions AS DOUBLE)), 0), 2)
      comment: "Cost per thousand impressions (CPM)"
    - name: "cpc"
      expr: ROUND(SUM(CAST(actual_spend_amount AS DOUBLE)) / NULLIF(SUM(CAST(clicks AS DOUBLE)), 0), 2)
      comment: "Cost per click (CPC)"
    - name: "avg_roi_index"
      expr: AVG(CAST(roi_index AS DOUBLE))
      comment: "Average ROI index for media spend"
$$;

-- source: ECM _metrics.marketing_consumer_insight  (over marketing.consumer_insight)  -> marketing_mart.marketing_consumer_insight
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`marketing_mart`.`marketing_consumer_insight`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Actionable consumer insight performance metrics"
  source: "`rongzi_catalog_dev`.`marketing_core`.`consumer_insight`"
  dimensions:
    - name: "brand_id"
      expr: brand_id
      comment: "Brand linked to the insight"
    - name: "sku_id"
      expr: sku_id
      comment: "SKU identifier"
    - name: "geography_scope"
      expr: geography_scope
      comment: "Geographic scope of the insight"
    - name: "insight_category"
      expr: insight_category
      comment: "Category of the insight (e.g., NPS, Sensory)"
    - name: "insight_priority"
      expr: insight_priority
      comment: "Priority level of the insight"
    - name: "deliverable_date"
      expr: deliverable_date
      comment: "Date the insight was delivered"
  measures:
    - name: "insight_record_count"
      expr: COUNT(1)
      comment: "Number of consumer insight records"
    - name: "total_actual_spend_usd"
      expr: SUM(CAST(actual_spend_usd AS DOUBLE))
      comment: "Total spend on consumer insight projects"
    - name: "avg_nps_score"
      expr: AVG(CAST(nps_score AS DOUBLE))
      comment: "Average NPS from consumer insights"
    - name: "avg_concept_test_score"
      expr: AVG(CAST(concept_test_score AS DOUBLE))
      comment: "Average concept test score"
    - name: "avg_sensory_score"
      expr: AVG(CAST(sensory_score AS DOUBLE))
      comment: "Average sensory score"
$$;

-- source: ECM _metrics.procurement_purchase_order  (over procurement.purchase_order)  -> procure_mart.procurement_purchase_order
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`procure_mart`.`procurement_purchase_order`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Key financial KPIs for purchase orders"
  source: "`rongzi_catalog_dev`.`procure_core`.`purchase_order`"
  dimensions:
    - name: "purchasing_org_code"
      expr: purchasing_org_code
      comment: "Purchasing organization code"
    - name: "supplier_id"
      expr: supplier_id
      comment: "Supplier identifier"
    - name: "po_status"
      expr: po_status
      comment: "Current status of the purchase order"
    - name: "order_date"
      expr: order_date
      comment: "Date the purchase order was created"
  measures:
    - name: "total_gross_amount"
      expr: SUM(CAST(po_gross_amount AS DOUBLE))
      comment: "Total gross amount of purchase orders"
    - name: "average_gross_amount"
      expr: AVG(CAST(po_gross_amount AS DOUBLE))
      comment: "Average gross amount per purchase order"
    - name: "total_net_amount"
      expr: SUM(CAST(net_amount AS DOUBLE))
      comment: "Total net amount of purchase orders"
    - name: "average_net_amount"
      expr: AVG(CAST(net_amount AS DOUBLE))
      comment: "Average net amount per purchase order"
    - name: "purchase_order_count"
      expr: COUNT(1)
      comment: "Number of purchase orders"
$$;

-- source: ECM _metrics.product_standard_cost  (over product.product_standard_cost)  -> master_mart.product_standard_cost
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`master_mart`.`product_standard_cost`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Standard cost components and overall cost per SKU."
  source: "`rongzi_catalog_dev`.`master_core`.`product_standard_cost`"
  dimensions:
    - name: "sku_id"
      expr: sku_id
      comment: "Stock Keeping Unit identifier"
    - name: "plant_id"
      expr: plant_id
      comment: "Manufacturing plant identifier"
    - name: "cost_center_id"
      expr: cost_center_id
      comment: "Cost center responsible for the cost"
    - name: "profit_center_id"
      expr: profit_center_id
      comment: "Profit center responsible for the cost"
    - name: "currency_code"
      expr: currency_code
      comment: "Currency of the cost values"
  measures:
    - name: "record_count"
      expr: COUNT(1)
      comment: "Number of standard cost records"
    - name: "avg_total_standard_cost_per_unit"
      expr: AVG(CAST(total_standard_cost_per_unit AS DOUBLE))
      comment: "Average total standard cost per unit"
    - name: "avg_total_standard_cost_per_case"
      expr: AVG(CAST(total_standard_cost_per_case AS DOUBLE))
      comment: "Average total standard cost per case"
    - name: "sum_raw_material_cost"
      expr: SUM(CAST(raw_material_cost AS DOUBLE))
      comment: "Sum of raw material cost across records"
    - name: "sum_freight_in_cost"
      expr: SUM(CAST(freight_in_cost AS DOUBLE))
      comment: "Sum of freight-in cost"
    - name: "sum_manufacturing_overhead_cost"
      expr: SUM(CAST(manufacturing_overhead_cost AS DOUBLE))
      comment: "Sum of manufacturing overhead cost"
$$;

-- source: ECM _metrics.sales_order  (over sales.order)  -> sales_mart.sales_order
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`sales_mart`.`sales_order`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Order level financial performance metrics"
  source: "`rongzi_catalog_dev`.`sales_core`.`order`"
  dimensions:
    - name: "order_status"
      expr: order_status
      comment: "Current status of the order"
    - name: "order_type"
      expr: order_type
      comment: "Classification of the order (e.g., standard, rush)"
    - name: "sales_region"
      expr: sales_region
      comment: "Geographic sales region"
    - name: "order_month"
      expr: DATE_TRUNC('month', placed_timestamp)
      comment: "Month of order placement"
    - name: "is_backorder"
      expr: is_backorder
      comment: "Flag indicating if the order is a backorder"
  measures:
    - name: "order_count"
      expr: COUNT(1)
      comment: "Number of orders"
    - name: "total_gross_amount"
      expr: SUM(CAST(total_gross_amount AS DOUBLE))
      comment: "Total gross amount across orders"
    - name: "total_net_amount"
      expr: SUM(CAST(total_net_amount AS DOUBLE))
      comment: "Total net amount across orders"
    - name: "total_discount_amount"
      expr: SUM(CAST(total_discount_amount AS DOUBLE))
      comment: "Total discount amount across orders"
    - name: "avg_gross_amount"
      expr: AVG(CAST(total_gross_amount AS DOUBLE))
      comment: "Average gross amount per order"
    - name: "avg_discount_amount"
      expr: AVG(CAST(total_discount_amount AS DOUBLE))
      comment: "Average discount amount per order"
$$;

-- source: ECM _metrics.sales_invoice  (over sales.invoice)  -> sales_mart.sales_invoice
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`sales_mart`.`sales_invoice`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Invoice financial summary metrics"
  source: "`rongzi_catalog_dev`.`sales_core`.`invoice`"
  dimensions:
    - name: "invoice_status"
      expr: invoice_status
      comment: "Current status of the invoice"
    - name: "invoice_type"
      expr: invoice_type
      comment: "Type of invoice (e.g., standard, credit memo)"
    - name: "currency_code"
      expr: currency_code
      comment: "Currency of the invoice"
    - name: "invoice_month"
      expr: DATE_TRUNC('month', invoice_date)
      comment: "Month of invoice issuance"
    - name: "is_credit_memo"
      expr: is_credit_memo
      comment: "Flag indicating if the invoice is a credit memo"
  measures:
    - name: "invoice_count"
      expr: COUNT(1)
      comment: "Number of invoices"
    - name: "total_amount"
      expr: SUM(CAST(total_amount AS DOUBLE))
      comment: "Total invoiced amount"
    - name: "subtotal_amount"
      expr: SUM(CAST(subtotal_amount AS DOUBLE))
      comment: "Sum of invoice subtotals"
    - name: "tax_amount"
      expr: SUM(CAST(tax_amount AS DOUBLE))
      comment: "Total tax collected on invoices"
    - name: "avg_total_amount"
      expr: AVG(CAST(total_amount AS DOUBLE))
      comment: "Average invoice total amount"
$$;

-- source: ECM _metrics.sales_rep  (over sales.rep)  -> sales_mart.sales_rep
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`sales_mart`.`sales_rep`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Sales representative performance and quota metrics"
  source: "`rongzi_catalog_dev`.`sales_core`.`rep`"
  dimensions:
    - name: "sales_region"
      expr: sales_region
      comment: "Region where the rep operates"
    - name: "sales_channel"
      expr: sales_channel
      comment: "Channel the rep sells through"
    - name: "rep_type"
      expr: rep_type
      comment: "Type of sales rep (e.g., field, inside)"
    - name: "employment_status"
      expr: employment_status
      comment: "Current employment status of the rep"
    - name: "is_remote_worker"
      expr: is_remote_worker
      comment: "Flag indicating if the rep works remotely"
  measures:
    - name: "rep_count"
      expr: COUNT(1)
      comment: "Number of sales representatives"
    - name: "avg_commission_rate_percent"
      expr: AVG(CAST(commission_rate_percent AS DOUBLE))
      comment: "Average commission rate percent across reps"
    - name: "total_quota_annual_revenue"
      expr: SUM(CAST(quota_annual_revenue AS DOUBLE))
      comment: "Total annual revenue quota assigned to reps"
    - name: "total_quota_annual_cases"
      expr: SUM(CAST(quota_annual_cases AS DOUBLE))
      comment: "Total annual case quota assigned to reps"
$$;

-- source: ECM _metrics.trade_promotion_event  (over trade.promotion_event)  -> trade_mart.trade_promotion_event
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`trade_mart`.`trade_promotion_event`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Core KPI view for promotion events covering revenue performance and volume"
  source: "`rongzi_catalog_dev`.`trade_core`.`promotion_event`"
  dimensions:
    - name: "promotion_type"
      expr: promotion_type
      comment: "Type of promotion (e.g., discount, bundle)"
  measures:
    - name: "promotion_event_count"
      expr: COUNT(1)
      comment: "Number of promotion events"
    - name: "total_actual_revenue"
      expr: SUM(CAST(actual_revenue AS DOUBLE))
      comment: "Sum of actual revenue generated by promotion events"
    - name: "total_target_revenue"
      expr: SUM(CAST(target_revenue AS DOUBLE))
      comment: "Sum of target revenue set for promotion events"
    - name: "average_actual_revenue"
      expr: AVG(CAST(actual_revenue AS DOUBLE))
      comment: "Average actual revenue per promotion event"
$$;

-- source: ECM _metrics.trade_promotion_line  (over trade.promotion_line)  -> trade_mart.trade_promotion_line
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`trade_mart`.`trade_promotion_line`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "KPIs for individual promotion lines, focusing on funding efficiency and margin"
  source: "`rongzi_catalog_dev`.`trade_core`.`promotion_line`"
  dimensions:
    - name: "promotion_type"
      expr: promotion_type
      comment: "Promotion line type (e.g., price, feature)"
  measures:
    - name: "promotion_line_count"
      expr: COUNT(1)
      comment: "Number of promotion line records"
    - name: "total_funding_amount"
      expr: SUM(CAST(total_funding_amount AS DOUBLE))
      comment: "Total funding allocated to promotion lines"
    - name: "total_quantity"
      expr: SUM(CAST(quantity AS DOUBLE))
      comment: "Total quantity of SKU units promoted"
    - name: "average_margin_per_unit"
      expr: AVG(CAST(margin_per_unit AS DOUBLE))
      comment: "Average margin per unit across promotion lines"
$$;

-- source: ECM _metrics.trade_settlement  (over trade.settlement)  -> trade_mart.trade_settlement
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`trade_mart`.`trade_settlement`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Financial settlement performance metrics"
  source: "`rongzi_catalog_dev`.`trade_core`.`settlement`"
  dimensions:
    - name: "settlement_status"
      expr: settlement_status
      comment: "Current status of the settlement"
  measures:
    - name: "settlement_count"
      expr: COUNT(1)
      comment: "Number of settlement records"
    - name: "total_net_amount"
      expr: SUM(CAST(net_amount AS DOUBLE))
      comment: "Total net amount settled"
    - name: "total_gross_amount"
      expr: SUM(CAST(gross_amount AS DOUBLE))
      comment: "Total gross amount settled"
    - name: "average_net_amount"
      expr: AVG(CAST(net_amount AS DOUBLE))
      comment: "Average net amount per settlement"
$$;

-- source: ECM _metrics.trade_fund  (over trade.fund)  -> trade_mart.trade_fund
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`trade_mart`.`trade_fund`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Fund allocation and utilization metrics"
  source: "`rongzi_catalog_dev`.`trade_core`.`fund`"
  dimensions:
    - name: "fund_type"
      expr: fund_type
      comment: "Classification of the fund (e.g., promotional, research)"
  measures:
    - name: "fund_count"
      expr: COUNT(1)
      comment: "Number of fund records"
    - name: "total_accrued_amount"
      expr: SUM(CAST(accrued_amount AS DOUBLE))
      comment: "Total amount accrued to funds"
    - name: "total_paid_amount"
      expr: SUM(CAST(paid_amount AS DOUBLE))
      comment: "Total amount paid from funds"
    - name: "average_accrued_amount"
      expr: AVG(CAST(accrued_amount AS DOUBLE))
      comment: "Average accrued amount per fund"
$$;

-- source: ECM _metrics.trade_accrual  (over trade.accrual)  -> trade_mart.trade_accrual
CREATE OR REPLACE VIEW `rongzi_catalog_dev`.`trade_mart`.`trade_accrual`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Accrual financial impact metrics"
  source: "`rongzi_catalog_dev`.`trade_core`.`accrual`"
  dimensions:
    - name: "accrual_status"
      expr: accrual_status
      comment: "Current status of the accrual"
  measures:
    - name: "accrual_count"
      expr: COUNT(1)
      comment: "Number of accrual records"
    - name: "total_amount"
      expr: SUM(CAST(amount AS DOUBLE))
      comment: "Total accrual amount"
    - name: "total_net_sales_amount"
      expr: SUM(CAST(net_sales_amount AS DOUBLE))
      comment: "Total net sales amount linked to accruals"
    - name: "average_amount"
      expr: AVG(CAST(amount AS DOUBLE))
      comment: "Average accrual amount per record"
$$;
