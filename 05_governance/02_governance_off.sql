-- 統治「前」の状態に戻す。評価のベースライン取得用。
--
-- 統治前 = 競合する metric view とダッシュボードからの推論だけで ontology が動いている状態。
--          認定なし・「売上ではない」注記なし・Page なし。
--          Genie One を有効にした初日の顧客そのもの。
--
-- Page は UI/API 側なので別手順（下書きに戻す or 削除）。このスクリプトは認定と注記を外す。

ALTER VIEW `rongzi_catalog_dev`.`finance_mart`.`finance_ar_invoice`           UNSET TAGS ('system.certification_status');
ALTER VIEW `rongzi_catalog_dev`.`sales_mart`.`sales_order`                    UNSET TAGS ('system.certification_status');
ALTER TABLE `rongzi_catalog_dev`.`xdept_mart`.`mart_revenue_definitions`      UNSET TAGS ('system.certification_status');
ALTER TABLE `rongzi_catalog_dev`.`finance_mart`.`mart_revenue_reconciliation` UNSET TAGS ('system.certification_status');
ALTER TABLE `rongzi_catalog_dev`.`xdept_mart`.`mart_customer_360`             UNSET TAGS ('system.certification_status');

-- 「売上ではない」注記を外し、ECM 由来の素のコメントに戻す
COMMENT ON VIEW `rongzi_catalog_dev`.`finance_mart`.`finance_ap_invoice` IS 'Accounts payable invoice financial metrics';
COMMENT ON VIEW `rongzi_catalog_dev`.`procure_mart`.`procurement_purchase_order` IS 'Purchase order financial and volume metrics';
COMMENT ON VIEW `rongzi_catalog_dev`.`trade_mart`.`trade_settlement` IS 'Trade settlement financial metrics';
COMMENT ON VIEW `rongzi_catalog_dev`.`sales_mart`.`sales_order` IS 'Order level financial performance metrics';
COMMENT ON VIEW `rongzi_catalog_dev`.`finance_mart`.`finance_ar_invoice` IS 'Accounts receivable invoice metrics';

-- マーケ（フェーズ2）の認定と注記を外す
ALTER VIEW  `rongzi_catalog_dev`.`marketing_mart`.`marketing_campaign_performance` UNSET TAGS ('system.certification_status');
ALTER TABLE `rongzi_catalog_dev`.`marketing_mart`.`mart_campaign_performance`      UNSET TAGS ('system.certification_status');
ALTER TABLE `rongzi_catalog_dev`.`marketing_mart`.`mart_brand_market_position`     UNSET TAGS ('system.certification_status');
ALTER TABLE `rongzi_catalog_dev`.`marketing_mart`.`mart_media_efficiency`          UNSET TAGS ('system.certification_status');
ALTER TABLE `rongzi_catalog_dev`.`xdept_mart`.`mart_spend_definitions`             UNSET TAGS ('system.certification_status');
ALTER TABLE `rongzi_catalog_dev`.`xdept_mart`.`mart_brand_investment_return`       UNSET TAGS ('system.certification_status');

-- ECM 由来の素のコメントに戻す（metric view は自分が所有しているので戻せる）
COMMENT ON VIEW `rongzi_catalog_dev`.`marketing_mart`.`marketing_campaign_performance` IS 'Key financial performance indicators for marketing campaigns';
COMMENT ON VIEW `rongzi_catalog_dev`.`marketing_mart`.`marketing_consumer_insight` IS 'Actionable consumer insight performance metrics';
COMMENT ON VIEW `rongzi_catalog_dev`.`marketing_mart`.`marketing_media_spend` IS 'Financial efficiency and reach metrics for media spend';
