-- 自動生成: 03_lakeflow/gen_pipeline.py
-- Brickshouse Food and Beverage / Lakeflow Spark Declarative Pipeline
-- bronze 30 本 → silver 30 本
-- 列名・型・コメントは業界データモデル(ECM)由来。expectations は自作。

-- bronze: sap_mm / sku  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`sap_mm__sku_raw`
COMMENT 'Bronze。sap_mm から取り込んだ sku の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'sap_mm'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/sap_mm__master_core__sku/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: sap_mm / category  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`sap_mm__category_raw`
COMMENT 'Bronze。sap_mm から取り込んだ category の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'sap_mm'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/sap_mm__master_core__category/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: sap_co / product_standard_cost  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`sap_co__product_standard_cost_raw`
COMMENT 'Bronze。sap_co から取り込んだ product_standard_cost の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'sap_co'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/sap_co__master_core__product_standard_cost/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: sap_fi / gl_account  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`sap_fi__gl_account_raw`
COMMENT 'Bronze。sap_fi から取り込んだ gl_account の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'sap_fi'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/sap_fi__finance_core__gl_account/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: sap_co / cost_center  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`sap_co__cost_center_raw`
COMMENT 'Bronze。sap_co から取り込んだ cost_center の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'sap_co'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/sap_co__finance_core__cost_center/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: sap_co / profit_center  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`sap_co__profit_center_raw`
COMMENT 'Bronze。sap_co から取り込んだ profit_center の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'sap_co'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/sap_co__finance_core__profit_center/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: sap_co / finance_standard_cost  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`sap_co__finance_standard_cost_raw`
COMMENT 'Bronze。sap_co から取り込んだ finance_standard_cost の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'sap_co'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/sap_co__finance_core__finance_standard_cost/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: sap_fi / ar_invoice  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`sap_fi__ar_invoice_raw`
COMMENT 'Bronze。sap_fi から取り込んだ ar_invoice の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'sap_fi'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/sap_fi__finance_core__ar_invoice/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: sap_fi / ap_invoice  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`sap_fi__ap_invoice_raw`
COMMENT 'Bronze。sap_fi から取り込んだ ap_invoice の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'sap_fi'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/sap_fi__finance_core__ap_invoice/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: sap_sd / order  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`sap_sd__order_raw`
COMMENT 'Bronze。sap_sd から取り込んだ order の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'sap_sd'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/sap_sd__sales_core__order/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: sap_sd / invoice  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`sap_sd__invoice_raw`
COMMENT 'Bronze。sap_sd から取り込んだ invoice の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'sap_sd'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/sap_sd__sales_core__invoice/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: salesforce / account  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`salesforce__account_raw`
COMMENT 'Bronze。salesforce から取り込んだ account の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'salesforce'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/salesforce__sales_core__account/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: workday / rep  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`workday__rep_raw`
COMMENT 'Bronze。workday から取り込んだ rep の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'workday'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/workday__sales_core__rep/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: salesforce / territory  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`salesforce__territory_raw`
COMMENT 'Bronze。salesforce から取り込んだ territory の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'salesforce'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/salesforce__sales_core__territory/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: pos_edi852 / pos_transaction  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`pos_edi852__pos_transaction_raw`
COMMENT 'Bronze。pos_edi852 から取り込んだ pos_transaction の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'pos_edi852'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/pos_edi852__sales_core__pos_transaction/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: nielsen / distribution_point  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`nielsen__distribution_point_raw`
COMMENT 'Bronze。nielsen から取り込んだ distribution_point の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'nielsen'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/nielsen__sales_core__distribution_point/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: tpm / fund  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`tpm__fund_raw`
COMMENT 'Bronze。tpm から取り込んだ fund の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'tpm'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/tpm__trade_core__fund/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: tpm / promotion_event  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`tpm__promotion_event_raw`
COMMENT 'Bronze。tpm から取り込んだ promotion_event の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'tpm'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/tpm__trade_core__promotion_event/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: tpm / promotion_line  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`tpm__promotion_line_raw`
COMMENT 'Bronze。tpm から取り込んだ promotion_line の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'tpm'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/tpm__trade_core__promotion_line/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: tpm / accrual  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`tpm__accrual_raw`
COMMENT 'Bronze。tpm から取り込んだ accrual の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'tpm'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/tpm__trade_core__accrual/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: tpm / settlement  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`tpm__settlement_raw`
COMMENT 'Bronze。tpm から取り込んだ settlement の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'tpm'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/tpm__trade_core__settlement/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: tpm / deduction  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`tpm__deduction_raw`
COMMENT 'Bronze。tpm から取り込んだ deduction の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'tpm'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/tpm__trade_core__deduction/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: sap_mm / supplier  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`sap_mm__supplier_raw`
COMMENT 'Bronze。sap_mm から取り込んだ supplier の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'sap_mm'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/sap_mm__procure_core__supplier/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: sap_mm / purchase_order  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`sap_mm__purchase_order_raw`
COMMENT 'Bronze。sap_mm から取り込んだ purchase_order の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'sap_mm'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/sap_mm__procure_core__purchase_order/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: salesforce_mc / brand  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`salesforce_mc__brand_raw`
COMMENT 'Bronze。salesforce_mc から取り込んだ brand の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'salesforce_mc'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/salesforce_mc__marketing_core__brand/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: salesforce_mc / campaign  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`salesforce_mc__campaign_raw`
COMMENT 'Bronze。salesforce_mc から取り込んだ campaign の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'salesforce_mc'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/salesforce_mc__marketing_core__campaign/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: salesforce_mc / campaign_execution  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`salesforce_mc__campaign_execution_raw`
COMMENT 'Bronze。salesforce_mc から取り込んだ campaign_execution の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'salesforce_mc'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/salesforce_mc__marketing_core__campaign_execution/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: mediaocean / media_spend  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`mediaocean__media_spend_raw`
COMMENT 'Bronze。mediaocean から取り込んだ media_spend の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'mediaocean'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/mediaocean__marketing_core__media_spend/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: nielsen_bases / consumer_insight  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`nielsen_bases__consumer_insight_raw`
COMMENT 'Bronze。nielsen_bases から取り込んだ consumer_insight の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'nielsen_bases'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/nielsen_bases__marketing_core__consumer_insight/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);

-- bronze: nielsen / syndicated_market_data  （生のまま・全列 STRING・取込メタデータ付与）
CREATE OR REFRESH STREAMING TABLE `rongzi_catalog_dev`.`ops_landing`.`nielsen__syndicated_market_data_raw`
COMMENT 'Bronze。nielsen から取り込んだ syndicated_market_data の生データ。型変換・名寄せはしない。'
AS SELECT
  *,
  _metadata.file_name   AS _ingest_file,
  _metadata.file_modification_time AS _ingest_time,
  'nielsen'               AS _source_system
FROM STREAM read_files(
  '/Volumes/rongzi_catalog_dev/ops_landing/raw/nielsen__marketing_core__syndicated_market_data/',
  format        => 'csv',
  header        => true,
  inferSchema   => false,
  schemaEvolutionMode => 'addNewColumns'
);
