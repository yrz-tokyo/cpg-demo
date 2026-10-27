-- Brickshouse Food and Beverage / gold 層
-- 部門別マート 6本 ＋ 横断マート 2本。すべて Lakeflow(SDP) が所有する MV。

-- ============================================================================
-- xdept_mart.mart_revenue_definitions
--   「売上」と呼ばれている5つの数字を、月次で1つの表に並べる。
--
--   受注の列は sales_order_* と書く。order_* だと発注(purchase_order_*)と1語違いになり、
--   原価率を聞かれた Genie が order_net_amount ÷ revenue_net_amount を計算して
--   122% と答えた（実測）。同じ表に受注と発注を並べるなら、名前で取り違えを防ぐ必要がある。
--   業界データモデル(ECM)の metric view は、このうち5つに total_net_amount という
--   完全同名の measure を持つ。どれを選ぶかで答えが最大15倍変わることを可視化する。
-- ============================================================================
CREATE OR REFRESH MATERIALIZED VIEW `rongzi_catalog_dev`.`xdept_mart`.`mart_revenue_definitions` (
  CONSTRAINT ex_month_present EXPECT (month_start IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT '部門ごとの金額を月次で1行に並べた横断マート。受注純額（営業）・請求総額・販促値引・控除・純売上（財務）・販促精算（販促）・買掛（財務）・発注（調達）・店頭実売（Nielsenパネルの投影値）。各列の出所はスキーマ名のとおり。'
AS
WITH o AS (
  SELECT date_trunc('month', placed_timestamp) AS month_start,
         SUM(total_gross_amount) AS sales_order_gross_amount,
         SUM(total_net_amount)   AS sales_order_net_amount,
         COUNT(*)                AS sales_order_count
  FROM `rongzi_catalog_dev`.`sales_core`.`order` GROUP BY 1
), ar AS (
  SELECT date_trunc('month', invoice_date) AS month_start,
         SUM(gross_amount)           AS invoiced_gross_amount,
         SUM(trade_discount_amount)  AS trade_discount_amount,
         SUM(deduction_amount)       AS deduction_amount,
         SUM(net_amount)             AS revenue_net_amount,
         COUNT(*)                    AS invoice_count
  FROM `rongzi_catalog_dev`.`finance_core`.`ar_invoice` GROUP BY 1
), st AS (
  SELECT date_trunc('month', accounting_date) AS month_start,
         SUM(net_amount) AS promo_settlement_net_amount
  FROM `rongzi_catalog_dev`.`trade_core`.`settlement` GROUP BY 1
), ap AS (
  SELECT date_trunc('month', invoice_date) AS month_start,
         SUM(net_amount) AS payable_net_amount
  FROM `rongzi_catalog_dev`.`finance_core`.`ap_invoice` GROUP BY 1
), po AS (
  SELECT date_trunc('month', order_date) AS month_start,
         SUM(net_amount) AS purchase_order_net_amount
  FROM `rongzi_catalog_dev`.`procure_core`.`purchase_order` GROUP BY 1
), pos AS (
  SELECT date_trunc('month', transaction_date) AS month_start,
         SUM(dollar_sales) AS panel_sellout_amount
  FROM `rongzi_catalog_dev`.`sales_core`.`pos_transaction` GROUP BY 1
)
SELECT
  COALESCE(o.month_start, ar.month_start, st.month_start, ap.month_start, po.month_start, pos.month_start) AS month_start,
  o.sales_order_gross_amount, o.sales_order_net_amount, o.sales_order_count,
  ar.invoiced_gross_amount, ar.trade_discount_amount, ar.deduction_amount,
  ar.revenue_net_amount, ar.invoice_count,
  st.promo_settlement_net_amount,
  ap.payable_net_amount,
  po.purchase_order_net_amount,
  pos.panel_sellout_amount,
  -- 受注と純売上の差（一部出荷・値引・販促控除の累積）
  o.sales_order_net_amount - ar.revenue_net_amount AS order_to_revenue_gap,
  ROUND(ar.revenue_net_amount / NULLIF(o.sales_order_net_amount, 0), 4) AS revenue_to_order_ratio
FROM o
FULL OUTER JOIN ar  ON o.month_start = ar.month_start
FULL OUTER JOIN st  ON COALESCE(o.month_start, ar.month_start) = st.month_start
FULL OUTER JOIN ap  ON COALESCE(o.month_start, ar.month_start) = ap.month_start
FULL OUTER JOIN po  ON COALESCE(o.month_start, ar.month_start) = po.month_start
FULL OUTER JOIN pos ON COALESCE(o.month_start, ar.month_start) = pos.month_start;


-- ============================================================================
-- xdept_mart.mart_customer_360
--   hub キー（account_id / sku_id）で部門を貫く結合の実証。
--   営業（受注・店頭）× 財務（請求・入金）× 販促（イベント・精算・控除）
-- ============================================================================
CREATE OR REFRESH MATERIALIZED VIEW `rongzi_catalog_dev`.`xdept_mart`.`mart_customer_360`
COMMENT '得意先を軸に、営業（受注・店頭実売）・財務（請求・純売上・未回収）・販促（販促費・精算・控除）を1行にまとめた横断マート。hub キー account_id が3部門を貫くことの実証。'
AS
WITH o AS (
  SELECT account_id, COUNT(*) AS order_count, SUM(total_net_amount) AS order_net_amount,
         MAX(placed_timestamp) AS last_order_at
  FROM `rongzi_catalog_dev`.`sales_core`.`order` GROUP BY 1
), ar AS (
  SELECT account_id,
         SUM(gross_amount) AS invoiced_gross_amount,
         SUM(net_amount) AS revenue_net_amount,
         SUM(open_amount) AS open_receivable_amount,
         SUM(trade_discount_amount + deduction_amount) AS revenue_leakage_amount
  FROM `rongzi_catalog_dev`.`finance_core`.`ar_invoice` GROUP BY 1
), pe AS (
  SELECT account_id, COUNT(*) AS promotion_count,
         SUM(promotional_spend_net) AS promo_spend_net_amount,
         SUM(actual_revenue) AS promo_actual_revenue
  FROM `rongzi_catalog_dev`.`trade_core`.`promotion_event` GROUP BY 1
), st AS (
  SELECT account_id, SUM(net_amount) AS promo_settlement_net_amount
  FROM `rongzi_catalog_dev`.`trade_core`.`settlement` GROUP BY 1
), dd AS (
  SELECT account_id, SUM(net_amount) AS deduction_net_amount
  FROM `rongzi_catalog_dev`.`trade_core`.`deduction` GROUP BY 1
), ps AS (
  SELECT account_id, SUM(dollar_sales) AS panel_sellout_amount, SUM(units_sold) AS panel_units
  FROM `rongzi_catalog_dev`.`sales_core`.`pos_transaction` GROUP BY 1
)
SELECT
  a.account_id, a.account_name, a.channel, a.shipping_state AS region,
  a.account_type, a.key_account_flag, a.annual_revenue_band,
  o.order_count, o.order_net_amount, o.last_order_at,
  ar.revenue_net_amount, ar.open_receivable_amount, ar.revenue_leakage_amount,
  pe.promotion_count, pe.promo_spend_net_amount, pe.promo_actual_revenue,
  st.promo_settlement_net_amount, dd.deduction_net_amount,
  ps.panel_sellout_amount, ps.panel_units,
  ROUND(ar.revenue_net_amount / NULLIF(o.order_net_amount, 0), 4) AS revenue_to_order_ratio,
  ROUND(pe.promo_spend_net_amount / NULLIF(ar.revenue_net_amount, 0), 4) AS promo_spend_ratio,
  ROUND(ar.revenue_leakage_amount / NULLIF(ar.invoiced_gross_amount, 0), 4) AS leakage_ratio
FROM `rongzi_catalog_dev`.`sales_core`.`account` a
LEFT JOIN o  ON a.account_id = o.account_id
LEFT JOIN ar ON a.account_id = ar.account_id
LEFT JOIN pe ON a.account_id = pe.account_id
LEFT JOIN st ON a.account_id = st.account_id
LEFT JOIN dd ON a.account_id = dd.account_id
LEFT JOIN ps ON a.account_id = ps.account_id;


-- ============================================================================
-- 営業マート
-- ============================================================================
CREATE OR REFRESH MATERIALIZED VIEW `rongzi_catalog_dev`.`sales_mart`.`mart_sales_performance`
COMMENT '営業の着地把握用マート。月 × 得意先 × チャネル × 地域 × 受注区分で受注を集計。ECM の sales ドメインに order_line が無く受注はヘッダ粒度のみのため、商品軸は pos_transaction / distribution_point / promotion_line 側で取る。'
AS
SELECT
  date_trunc('month', o.placed_timestamp) AS month_start,
  o.account_id, a.account_name, o.channel, o.sales_region,
  o.order_status, o.order_type, o.order_source,
  COUNT(*)                        AS order_count,
  SUM(o.total_quantity)           AS order_quantity,
  SUM(o.total_gross_amount)       AS order_gross_amount,
  SUM(o.total_discount_amount)    AS order_discount_amount,
  SUM(o.total_net_amount)         AS order_net_amount,
  SUM(CASE WHEN o.is_backorder THEN 1 ELSE 0 END) AS backorder_count,
  SUM(CASE WHEN o.trade_allowance_flag THEN o.total_net_amount ELSE 0 END) AS trade_allowance_order_amount
FROM `rongzi_catalog_dev`.`sales_core`.`order` o
LEFT JOIN `rongzi_catalog_dev`.`sales_core`.`account` a ON o.account_id = a.account_id
GROUP BY 1,2,3,4,5,6,7,8;


CREATE OR REFRESH MATERIALIZED VIEW `rongzi_catalog_dev`.`sales_mart`.`mart_account_coverage`
COMMENT '配下率（ACV 加重配下・numeric 配下・TDP）を得意先 × 商品 × 期間で集計した営業マート。出所は Nielsen パネル。'
AS
SELECT
  d.snapshot_date, d.period_type,
  d.account_id, a.account_name, a.channel, a.shipping_state AS region,
  s.product_line, s.flavor_variety,
  COUNT(*)                                     AS point_count,
  AVG(d.acv_weighted_distribution_pct)         AS avg_acv_weighted_pct,
  AVG(d.numeric_distribution_pct)              AS avg_numeric_pct,
  SUM(d.tdp_contribution_pct)                  AS tdp_contribution_pct,
  AVG(d.acv_change_pct)                        AS avg_acv_change_pct,
  AVG(d.velocity_units_per_point)              AS avg_velocity_units_per_point,
  SUM(CASE WHEN d.in_stock_flag THEN 0 ELSE 1 END) AS out_of_stock_points
FROM `rongzi_catalog_dev`.`sales_core`.`distribution_point` d
LEFT JOIN `rongzi_catalog_dev`.`sales_core`.`account` a ON d.account_id = a.account_id
LEFT JOIN `rongzi_catalog_dev`.`master_core`.`sku` s    ON d.sku_id = s.sku_id
GROUP BY 1,2,3,4,5,6,7,8;


-- ============================================================================
-- 財務マート
-- ============================================================================
CREATE OR REFRESH MATERIALIZED VIEW `rongzi_catalog_dev`.`finance_mart`.`mart_revenue_reconciliation` (
  CONSTRAINT ex_recon_closes EXPECT (
    abs(revenue_net_amount - (invoiced_gross_amount - trade_discount_amount - deduction_amount)) < 100
  )
)
COMMENT '財務の売上照合マート。受注 → 請求総額 → 販促値引・控除 → 純売上 の各段を得意先 × 月で並べ、段ごとの差分を出す。'
AS
SELECT
  date_trunc('month', ar.invoice_date) AS month_start,
  ar.account_id, a.account_name, a.channel,
  ar.invoice_status,
  COUNT(*)                            AS invoice_count,
  SUM(ar.gross_amount)                AS invoiced_gross_amount,
  SUM(ar.trade_discount_amount)       AS trade_discount_amount,
  SUM(ar.deduction_amount)            AS deduction_amount,
  SUM(ar.net_amount)                  AS revenue_net_amount,
  SUM(ar.tax_amount)                  AS tax_amount,
  SUM(ar.payment_amount)              AS payment_amount,
  SUM(ar.open_amount)                 AS open_receivable_amount,
  SUM(ar.short_payment_amount)        AS short_payment_amount
FROM `rongzi_catalog_dev`.`finance_core`.`ar_invoice` ar
LEFT JOIN `rongzi_catalog_dev`.`sales_core`.`account` a ON ar.account_id = a.account_id
GROUP BY 1,2,3,4,5;


CREATE OR REFRESH MATERIALIZED VIEW `rongzi_catalog_dev`.`finance_mart`.`mart_standard_cost_compare`
COMMENT '2つの標準原価を並べた財務マート。製品側（master_core.product_standard_cost）と財務側（finance_core.finance_standard_cost）で単位原価が一致しない箇所を洗い出す。'
AS
SELECT
  p.sku_id, s.product_name, s.product_line,
  p.cost_version,
  p.total_standard_cost_per_unit    AS product_side_unit_cost,
  p.raw_material_cost               AS product_side_material_cost,
  p.cost_variance_percentage        AS product_side_variance_pct,
  f.standard_price_per_unit         AS finance_side_unit_cost,
  f.raw_material_cost               AS finance_side_material_cost,
  f.variance_percentage             AS finance_side_variance_pct,
  p.total_standard_cost_per_unit - f.standard_price_per_unit AS unit_cost_gap,
  ROUND(ABS(p.total_standard_cost_per_unit - f.standard_price_per_unit)
        / NULLIF(f.standard_price_per_unit, 0), 4) AS unit_cost_gap_ratio
FROM `rongzi_catalog_dev`.`master_core`.`product_standard_cost` p
LEFT JOIN `rongzi_catalog_dev`.`master_core`.`sku` s ON p.sku_id = s.sku_id
LEFT JOIN `rongzi_catalog_dev`.`finance_core`.`finance_standard_cost` f
       ON p.product_standard_cost_id = f.finance_standard_cost_id;


-- ============================================================================
-- 販促マート
-- ============================================================================
CREATE OR REFRESH MATERIALIZED VIEW `rongzi_catalog_dev`.`trade_mart`.`mart_promotion_roi`
COMMENT '販促ROIマート。イベント単位の計画/実績の売上とリフト、販促費、ROI。actual_revenue は販促システム側の入力値で、財務の純売上とは一致しない。'
AS
SELECT
  pe.promotion_event_id, pe.event_number,
  pe.account_id, a.account_name, pe.channel, pe.product_category,
  pe.promotion_type, pe.mechanic_type, pe.promotion_objective, pe.promotion_event_status,
  pe.planned_start_date, pe.planned_end_date,
  pe.promotional_spend_gross, pe.promotional_spend_net,
  pe.target_revenue, pe.actual_revenue,
  pe.target_sales_volume, pe.actual_sales_volume,
  pe.store_count_planned, pe.store_count_actual,
  ROUND((pe.actual_revenue - pe.promotional_spend_net) / NULLIF(pe.promotional_spend_net, 0), 4) AS roi,
  ROUND(pe.actual_revenue / NULLIF(pe.target_revenue, 0), 4)       AS revenue_attainment,
  ROUND(pe.actual_sales_volume / NULLIF(pe.target_sales_volume, 0), 4) AS volume_attainment
FROM `rongzi_catalog_dev`.`trade_core`.`promotion_event` pe
LEFT JOIN `rongzi_catalog_dev`.`sales_core`.`account` a ON pe.account_id = a.account_id;


CREATE OR REFRESH MATERIALIZED VIEW `rongzi_catalog_dev`.`trade_mart`.`mart_trade_spend_flow`
COMMENT '販促費の流れを月次で追う販促マート。引当（accrual）→ 精算（settlement）→ 控除（deduction）の3段を並べ、引当残と精算差異を出す。'
AS
WITH ac AS (
  SELECT date_trunc('month', effective_date) AS month_start,
         SUM(amount) AS accrual_amount, COUNT(*) AS accrual_count,
         SUM(CASE WHEN reversal_flag THEN amount ELSE 0 END) AS reversed_amount
  FROM `rongzi_catalog_dev`.`trade_core`.`accrual` GROUP BY 1
), se AS (
  SELECT date_trunc('month', accounting_date) AS month_start,
         SUM(original_claim_amount) AS claim_amount,
         SUM(adjustment_amount)     AS adjustment_amount,
         SUM(net_amount)            AS settled_amount, COUNT(*) AS settlement_count
  FROM `rongzi_catalog_dev`.`trade_core`.`settlement` GROUP BY 1
), de AS (
  SELECT date_trunc('month', deduction_date) AS month_start,
         SUM(net_amount) AS deduction_amount, COUNT(*) AS deduction_count,
         SUM(CASE WHEN dispute_flag THEN net_amount ELSE 0 END) AS disputed_amount
  FROM `rongzi_catalog_dev`.`trade_core`.`deduction` GROUP BY 1
)
SELECT
  COALESCE(ac.month_start, se.month_start, de.month_start) AS month_start,
  ac.accrual_amount, ac.accrual_count, ac.reversed_amount,
  se.claim_amount, se.adjustment_amount, se.settled_amount, se.settlement_count,
  de.deduction_amount, de.deduction_count, de.disputed_amount,
  ac.accrual_amount - se.settled_amount AS accrual_to_settlement_gap,
  ROUND(se.settled_amount / NULLIF(ac.accrual_amount, 0), 4) AS settlement_rate
FROM ac
FULL OUTER JOIN se ON ac.month_start = se.month_start
FULL OUTER JOIN de ON COALESCE(ac.month_start, se.month_start) = de.month_start;


-- ============================================================================
-- xdept_mart.mart_spend_definitions
--   「マーケに使ったお金」と呼ばれている5つの数字を、月次で1つの表に並べる。
--   mart_revenue_definitions の投資側の対。通貨列を必ず持たせて、
--   USD と JPY を足せないことを表の構造として表現する。
-- ============================================================================
CREATE OR REFRESH MATERIALIZED VIEW `rongzi_catalog_dev`.`xdept_mart`.`mart_spend_definitions` (
  CONSTRAINT ex_month_present EXPECT (month_start IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'マーケと販促の支出を月次で1行に並べた横断マート。キャンペーン投下(USD)・媒体費(USD)・執行実績(USD)・消費者調査費(USD)・販促精算(JPY)。列名の接尾辞 _usd / _jpy が建値を表す。建値が混ざるため合計列は持たない。'
AS
WITH cmp AS (
  SELECT date_trunc('month', start_date) AS month_start,
         SUM(planned_budget_usd) AS campaign_planned_usd,
         SUM(actual_spend_usd)   AS campaign_actual_usd,
         COUNT(*)                AS campaign_count
  FROM `rongzi_catalog_dev`.`marketing_core`.`campaign` GROUP BY 1
), med AS (
  SELECT date_trunc('month', spend_date) AS month_start,
         SUM(planned_spend_amount) AS media_planned_usd,
         SUM(actual_spend_amount)  AS media_actual_usd,
         SUM(impressions)          AS media_impressions,
         COUNT(*)                  AS media_line_count
  FROM `rongzi_catalog_dev`.`marketing_core`.`media_spend` GROUP BY 1
), exe AS (
  SELECT date_trunc('month', flight_start_date) AS month_start,
         SUM(planned_spend_amount) AS execution_planned_usd,
         SUM(actual_spend_amount)  AS execution_actual_usd,
         COUNT(*)                  AS execution_count
  FROM `rongzi_catalog_dev`.`marketing_core`.`campaign_execution` GROUP BY 1
), ins AS (
  SELECT date_trunc('month', deliverable_date) AS month_start,
         SUM(actual_spend_usd) AS consumer_insight_usd,
         COUNT(*)              AS study_count
  FROM `rongzi_catalog_dev`.`marketing_core`.`consumer_insight` GROUP BY 1
), tra AS (
  SELECT date_trunc('month', accounting_date) AS month_start,
         SUM(net_amount) AS trade_settled_jpy
  FROM `rongzi_catalog_dev`.`trade_core`.`settlement` GROUP BY 1
)
SELECT
  COALESCE(cmp.month_start, med.month_start, exe.month_start, ins.month_start, tra.month_start) AS month_start,
  cmp.campaign_planned_usd, cmp.campaign_actual_usd, cmp.campaign_count,
  med.media_planned_usd, med.media_actual_usd, med.media_impressions, med.media_line_count,
  exe.execution_planned_usd, exe.execution_actual_usd, exe.execution_count,
  ins.consumer_insight_usd, ins.study_count,
  tra.trade_settled_jpy,
  -- 調査費が投下額の何%か。取り違えの倍率がそのまま見える
  ROUND(ins.consumer_insight_usd / NULLIF(cmp.campaign_actual_usd, 0), 4) AS insight_to_campaign_ratio,
  -- 媒体費が投下額のどれだけを占めるか（残りが制作費・代理店フィー等）
  ROUND(med.media_actual_usd / NULLIF(cmp.campaign_actual_usd, 0), 4)    AS media_to_campaign_ratio,
  ROUND(cmp.campaign_actual_usd / NULLIF(cmp.campaign_planned_usd, 0), 4) AS campaign_burn_rate
FROM cmp
FULL OUTER JOIN med ON cmp.month_start = med.month_start
FULL OUTER JOIN exe ON COALESCE(cmp.month_start, med.month_start) = exe.month_start
FULL OUTER JOIN ins ON COALESCE(cmp.month_start, med.month_start, exe.month_start) = ins.month_start
FULL OUTER JOIN tra ON COALESCE(cmp.month_start, med.month_start, exe.month_start, ins.month_start) = tra.month_start;


-- ============================================================================
-- marketing_mart.mart_campaign_performance
--   キャンペーン単位の計画・投下・執行・媒体。現場の「消化できていない施策」の置き場。
-- ============================================================================
CREATE OR REFRESH MATERIALIZED VIEW `rongzi_catalog_dev`.`marketing_mart`.`mart_campaign_performance`
COMMENT 'キャンペーン単位のマーケマート。計画予算・投下実績・執行明細の合計・媒体費を1行に並べ、消化率とCPMを出す。金額はすべて USD 建て（currency_code 列を参照）。'
AS
WITH ex AS (
  SELECT campaign_id,
         SUM(planned_spend_amount)   AS execution_planned_usd,
         SUM(actual_spend_amount)    AS execution_actual_usd,
         SUM(impressions_delivered)  AS impressions_delivered,
         SUM(clicks_delivered)       AS clicks_delivered,
         COUNT(*)                    AS execution_count,
         SUM(CASE WHEN actual_spend_amount < planned_spend_amount * 0.7 THEN 1 ELSE 0 END) AS underspent_executions
  FROM `rongzi_catalog_dev`.`marketing_core`.`campaign_execution` GROUP BY 1
), ms AS (
  SELECT campaign_id,
         SUM(actual_spend_amount) AS media_actual_usd,
         SUM(agency_fee_amount)   AS agency_fee_usd,
         SUM(impressions)         AS media_impressions,
         AVG(roi_index)           AS avg_media_roi_index,
         COUNT(*)                 AS media_line_count
  FROM `rongzi_catalog_dev`.`marketing_core`.`media_spend` GROUP BY 1
)
SELECT
  c.campaign_id, c.campaign_code, c.campaign_name, c.campaign_type, c.channel, c.objective,
  c.brand_id, b.brand_name, b.brand_category, b.owner_division,
  c.start_date, c.end_date, c.fiscal_period, c.campaign_status, c.approval_status,
  c.currency_code,
  c.planned_budget_usd, c.actual_spend_usd,
  ex.execution_planned_usd, ex.execution_actual_usd, ex.execution_count, ex.underspent_executions,
  ms.media_actual_usd, ms.agency_fee_usd, ms.media_line_count, ms.avg_media_roi_index,
  COALESCE(ex.impressions_delivered, 0) + COALESCE(ms.media_impressions, 0) AS total_impressions,
  ex.clicks_delivered,
  ROUND(c.actual_spend_usd / NULLIF(c.planned_budget_usd, 0), 4) AS burn_rate,
  ROUND(1000.0 * c.actual_spend_usd
        / NULLIF(COALESCE(ex.impressions_delivered, 0) + COALESCE(ms.media_impressions, 0), 0), 2) AS cpm_usd,
  c.media_impressions_target, c.reach_target_households, c.acv_target_pct
FROM `rongzi_catalog_dev`.`marketing_core`.`campaign` c
LEFT JOIN `rongzi_catalog_dev`.`marketing_core`.`brand` b ON c.brand_id = b.brand_id
LEFT JOIN ex ON c.campaign_id = ex.campaign_id
LEFT JOIN ms ON c.campaign_id = ms.campaign_id;


-- ============================================================================
-- marketing_mart.mart_brand_market_position
--   syndicated（市場全体・USD）と 自社 POS（パネル投影・JPY）を、
--   足さずに並べる。dollar_sales という同名列が別物であることを表の形で示す。
-- ============================================================================
CREATE OR REFRESH MATERIALIZED VIEW `rongzi_catalog_dev`.`marketing_mart`.`mart_brand_market_position`
COMMENT 'ブランド×地域×月のマーケマート。market_dollar_sales_usd は Nielsen syndicated の市場全体（競合を含む・USD）、own_panel_sellout_jpy は自社の店頭実売（Nielsen パネルの約15% ACV 投影値・JPY）。元のテーブルではどちらも dollar_sales という列名。建値と universe が違うため合計列は持たない。'
AS
WITH syn AS (
  SELECT brand_id,
         date_trunc('month', period_start_date) AS month_start,
         market_name,
         SUM(dollar_sales)          AS market_dollar_sales_usd,
         SUM(promoted_dollar_sales) AS market_promoted_dollar_sales_usd,
         AVG(dollar_share_pct)      AS own_dollar_share_pct,
         AVG(unit_share_pct)        AS own_unit_share_pct,
         AVG(acv_distribution_pct)  AS acv_distribution_pct,
         AVG(tdp)                   AS tdp,
         AVG(dollar_sales_change_pct) AS market_growth_pct
  FROM `rongzi_catalog_dev`.`marketing_core`.`syndicated_market_data`
  WHERE market_type = 'category_total'
  GROUP BY 1, 2, 3
), pos AS (
  SELECT s.brand_id,
         date_trunc('month', p.transaction_date) AS month_start,
         SUM(p.dollar_sales) AS own_panel_sellout_jpy,
         SUM(p.units_sold)   AS own_panel_units
  FROM `rongzi_catalog_dev`.`sales_core`.`pos_transaction` p
  JOIN `rongzi_catalog_dev`.`master_core`.`sku` s ON p.sku_id = s.sku_id
  GROUP BY 1, 2
)
SELECT
  syn.brand_id, b.brand_name, b.brand_category, b.owner_division,
  syn.month_start, syn.market_name,
  syn.market_dollar_sales_usd,
  syn.market_promoted_dollar_sales_usd,
  syn.own_dollar_share_pct, syn.own_unit_share_pct,
  syn.acv_distribution_pct, syn.tdp, syn.market_growth_pct,
  pos.own_panel_sellout_jpy, pos.own_panel_units,
  -- 市場全体に自社シェアを掛けた「自社の市場売上（USD）」。POS とは出所も通貨も違う
  ROUND(syn.market_dollar_sales_usd * syn.own_dollar_share_pct / 100.0, 2) AS own_market_sales_usd,
  b.awareness_pct, b.equity_score, b.nps_score
FROM syn
LEFT JOIN `rongzi_catalog_dev`.`marketing_core`.`brand` b ON syn.brand_id = b.brand_id
LEFT JOIN pos ON syn.brand_id = pos.brand_id AND syn.month_start = pos.month_start;


-- ============================================================================
-- xdept_mart.mart_brand_investment_return
--   ブランド別の投資と戻り。ROI の「正しい計算の置き場」。
--   分子・分母の出所と通貨と換算レートを、表の中に書き切ってしまう。
--   ここが metric view / マートの価値が最も出るところ:
--   同じ ROI を3部門が別々に計算すると3つ出るが、この表を通せば1つになる。
-- ============================================================================
CREATE OR REFRESH MATERIALIZED VIEW `rongzi_catalog_dev`.`xdept_mart`.`mart_brand_investment_return`
COMMENT 'ブランド別の投資対効果マート。【分子】brand_sales_jpy ＝ Nielsen syndicated の市場全体 × 自社シェア を JPY 換算したブランド売上。ECM の受注はヘッダ粒度で sku_id を持たず財務の純売上をブランドに割れないため、CPG の実務標準どおり syndicated から推計する。syndicated は小売店頭価格での sell-through なので、卸値ベースの純売上より小売マージン分だけ高く出る（約1.2〜1.4倍）。この比率が妥当な範囲にあることで推計の筋を検算できる。POS のパネル投影値は panel_sellout_jpy 列に検算用として併記してあるが、投影率が低く絶対額が小さいので ROI の分子には使わない。【分母】マーケ投下は USD 建てなので marketing_spend_fx_rate（1USD=150JPY）で換算してから販促費(JPY)と足している。根拠は fx_basis 列に明示。【用途】ブランド間の相対比較と投資配分。推計値なので全社 P/L の粗利とは一致しない。'
AS
WITH mkt AS (
  SELECT brand_id,
         SUM(actual_spend_usd)   AS campaign_actual_usd,
         SUM(planned_budget_usd) AS campaign_planned_usd,
         COUNT(*)                AS campaign_count
  FROM `rongzi_catalog_dev`.`marketing_core`.`campaign` GROUP BY 1
), ins AS (
  SELECT brand_id, SUM(actual_spend_usd) AS consumer_insight_usd, COUNT(*) AS study_count
  FROM `rongzi_catalog_dev`.`marketing_core`.`consumer_insight` GROUP BY 1
), tpm AS (
  SELECT brand_id,
         SUM(total_funding_amount) AS trade_funding_jpy,
         SUM(budget_amount)        AS trade_budget_jpy,
         COUNT(*)                  AS promotion_line_count
  FROM `rongzi_catalog_dev`.`trade_core`.`promotion_line` GROUP BY 1
), pos AS (
  SELECT s.brand_id,
         SUM(p.dollar_sales) AS panel_sellout_jpy,
         SUM(p.units_sold)   AS panel_units
  FROM `rongzi_catalog_dev`.`sales_core`.`pos_transaction` p
  JOIN `rongzi_catalog_dev`.`master_core`.`sku` s ON p.sku_id = s.sku_id
  GROUP BY 1
), shr AS (
  -- ブランド売上の推計: 市場全体 × 自社シェア。
  -- market_name は8地域で、合計が全国の universe になる（「全国」という行は持たない）。
  SELECT brand_id,
         AVG(dollar_share_pct) AS avg_dollar_share_pct,
         SUM(dollar_sales * dollar_share_pct / 100.0) AS brand_sales_usd,
         SUM(dollar_sales) AS market_dollar_sales_usd
  FROM `rongzi_catalog_dev`.`marketing_core`.`syndicated_market_data`
  WHERE market_type = 'category_total' GROUP BY 1
)
SELECT
  b.brand_id, b.brand_name, b.brand_category, b.owner_division, b.lifecycle_status,
  150.0 AS marketing_spend_fx_rate,
  'USD->JPY 固定 150.0（デモ用。実務では期中平均レートを使う）' AS fx_basis,
  mkt.campaign_actual_usd, mkt.campaign_planned_usd, mkt.campaign_count,
  ins.consumer_insight_usd, ins.study_count,
  tpm.trade_funding_jpy, tpm.trade_budget_jpy, tpm.promotion_line_count,
  pos.panel_sellout_jpy, pos.panel_units,
  shr.avg_dollar_share_pct, shr.market_dollar_sales_usd, shr.brand_sales_usd,
  ROUND(COALESCE(mkt.campaign_actual_usd, 0) * 150.0, 2) AS campaign_actual_jpy,
  ROUND(COALESCE(mkt.campaign_actual_usd, 0) * 150.0 + COALESCE(tpm.trade_funding_jpy, 0), 2)
    AS total_investment_jpy,
  -- ブランド売上（推計・JPY）。ROI の分子はこれ
  ROUND(shr.brand_sales_usd * 150.0, 2) AS brand_sales_jpy,
  ROUND(shr.brand_sales_usd * 150.0
        / NULLIF(COALESCE(mkt.campaign_actual_usd, 0) * 150.0 + COALESCE(tpm.trade_funding_jpy, 0), 0), 4)
    AS return_on_investment,
  -- 検算用: POS パネル投影値を分子にした場合。投影率が低いので絶対値は小さい
  ROUND(pos.panel_sellout_jpy
        / NULLIF(COALESCE(mkt.campaign_actual_usd, 0) * 150.0 + COALESCE(tpm.trade_funding_jpy, 0), 0), 4)
    AS roi_on_panel_basis,
  b.awareness_pct, b.equity_score, b.nps_score, b.annual_marketing_budget, b.budget_currency_code
FROM `rongzi_catalog_dev`.`marketing_core`.`brand` b
LEFT JOIN mkt ON b.brand_id = mkt.brand_id
LEFT JOIN ins ON b.brand_id = ins.brand_id
LEFT JOIN tpm ON b.brand_id = tpm.brand_id
LEFT JOIN pos ON b.brand_id = pos.brand_id
LEFT JOIN shr ON b.brand_id = shr.brand_id;


-- ============================================================================
-- marketing_mart.mart_media_efficiency
--   媒体チャネル別の効率。現場ペルソナの日々の問いの置き場。
-- ============================================================================
CREATE OR REFRESH MATERIALIZED VIEW `rongzi_catalog_dev`.`marketing_mart`.`mart_media_efficiency`
COMMENT '媒体チャネル×月のマーケマート。投下額・インプレッション・クリック・CPM・CPC・ROI指数。金額は USD 建て。currency_code が空の明細の件数を missing_currency_rows 列に出している。'
AS
SELECT
  date_trunc('month', spend_date) AS month_start,
  media_channel, media_type, buying_type,
  SUM(planned_spend_amount) AS planned_spend_usd,
  SUM(actual_spend_amount)  AS actual_spend_usd,
  SUM(agency_fee_amount)    AS agency_fee_usd,
  SUM(impressions)          AS impressions,
  SUM(clicks)               AS clicks,
  SUM(reach)                AS reach,
  COUNT(*)                  AS line_count,
  SUM(CASE WHEN currency_code IS NULL OR currency_code = '' THEN 1 ELSE 0 END) AS missing_currency_rows,
  SUM(CASE WHEN working_media_flag THEN actual_spend_amount ELSE 0 END) AS working_media_usd,
  ROUND(1000.0 * SUM(actual_spend_amount) / NULLIF(SUM(impressions), 0), 2) AS cpm_usd,
  ROUND(SUM(actual_spend_amount) / NULLIF(SUM(clicks), 0), 2)              AS cpc_usd,
  ROUND(100.0 * SUM(clicks) / NULLIF(SUM(impressions), 0), 4)              AS ctr_pct,
  ROUND(AVG(roi_index), 4) AS avg_roi_index,
  ROUND(SUM(actual_spend_amount) / NULLIF(SUM(planned_spend_amount), 0), 4) AS burn_rate
FROM `rongzi_catalog_dev`.`marketing_core`.`media_spend`
GROUP BY 1, 2, 3, 4;
