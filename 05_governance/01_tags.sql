-- Brickshouse / UC ガバナンス: ドメインと subdomain
--
-- 重要: カタログには絶対にドメインタグを付けない。
--   docs: カタログまたはスキーマにドメインタグを付けると配下の資産が継承し、
--         継承されたタグは個別資産から外せない。カタログは1つしか無いので、
--         付けた瞬間に全スキーマが1ドメインに固定され二度と戻せない。
--
-- 構成（2026-10-26 に subdomain 化）
--   Brickshouse Food and Beverage              ← 親。全社共通と横断をここに置く
--     ├─ /営業          値: 営業 | 販促        ← 販促は営業の中の機能なので「値」で区別する
--     ├─ /財務          値: 財務
--     └─ /マーケティング  値: マーケティング
--
-- 当初は governed tag `brickshouse_department` で部門を表していたが、
-- アカウントのドメイン枠が空いたので subdomain に置き換えた。
-- subdomain のほうが Discover のドメインフィルタに階層で出て、Page を部門配下に置ける。
-- `brickshouse_department` は役目が subdomain と重複するので削除した。
--
-- タグポリシーの枠はアカウントで上限（実測 3,074）。新規作成には先に自分のものを消す必要がある。
-- tag_key は IMMUTABLE で改名できないため、削除 → 作成しか道がない。

-- 業務スキーマ -> 親ドメイン
ALTER SCHEMA `rongzi_catalog_dev`.`master_core`     SET TAGS ('Brickshouse Food and Beverage' = 'master');
ALTER SCHEMA `rongzi_catalog_dev`.`master_mart`     SET TAGS ('Brickshouse Food and Beverage' = 'master');
ALTER SCHEMA `rongzi_catalog_dev`.`sales_core`      SET TAGS ('Brickshouse Food and Beverage' = 'sales');
ALTER SCHEMA `rongzi_catalog_dev`.`sales_mart`      SET TAGS ('Brickshouse Food and Beverage' = 'sales');
ALTER SCHEMA `rongzi_catalog_dev`.`finance_core`    SET TAGS ('Brickshouse Food and Beverage' = 'finance');
ALTER SCHEMA `rongzi_catalog_dev`.`finance_mart`    SET TAGS ('Brickshouse Food and Beverage' = 'finance');
ALTER SCHEMA `rongzi_catalog_dev`.`trade_core`      SET TAGS ('Brickshouse Food and Beverage' = 'trade');
ALTER SCHEMA `rongzi_catalog_dev`.`trade_mart`      SET TAGS ('Brickshouse Food and Beverage' = 'trade');
ALTER SCHEMA `rongzi_catalog_dev`.`marketing_core`  SET TAGS ('Brickshouse Food and Beverage' = 'marketing');
ALTER SCHEMA `rongzi_catalog_dev`.`marketing_mart`  SET TAGS ('Brickshouse Food and Beverage' = 'marketing');
ALTER SCHEMA `rongzi_catalog_dev`.`procure_core`    SET TAGS ('Brickshouse Food and Beverage' = 'procurement');
ALTER SCHEMA `rongzi_catalog_dev`.`procure_mart`    SET TAGS ('Brickshouse Food and Beverage' = 'procurement');
ALTER SCHEMA `rongzi_catalog_dev`.`xdept_mart`      SET TAGS ('Brickshouse Food and Beverage' = 'cross-department');

-- 部門 subdomain。親タグと併存させる（親ドメインへロールアップさせるため両方付ける）
ALTER SCHEMA `rongzi_catalog_dev`.`sales_core`      SET TAGS ('Brickshouse Food and Beverage/営業' = '営業');
ALTER SCHEMA `rongzi_catalog_dev`.`sales_mart`      SET TAGS ('Brickshouse Food and Beverage/営業' = '営業');
ALTER SCHEMA `rongzi_catalog_dev`.`trade_core`      SET TAGS ('Brickshouse Food and Beverage/営業' = '販促');
ALTER SCHEMA `rongzi_catalog_dev`.`trade_mart`      SET TAGS ('Brickshouse Food and Beverage/営業' = '販促');
ALTER SCHEMA `rongzi_catalog_dev`.`finance_core`    SET TAGS ('Brickshouse Food and Beverage/財務' = '財務');
ALTER SCHEMA `rongzi_catalog_dev`.`finance_mart`    SET TAGS ('Brickshouse Food and Beverage/財務' = '財務');
ALTER SCHEMA `rongzi_catalog_dev`.`marketing_core`  SET TAGS ('Brickshouse Food and Beverage/マーケティング' = 'マーケティング');
ALTER SCHEMA `rongzi_catalog_dev`.`marketing_mart`  SET TAGS ('Brickshouse Food and Beverage/マーケティング' = 'マーケティング');

-- ops_landing / semantics_ops / platform_ops は業務ドメインではないのでタグを付けない
-- （業務ユーザーに見せない層。Grant でも閉じる）
ALTER SCHEMA `rongzi_catalog_dev`.`ops_landing`     SET OWNER TO `rongzi.yan@databricks.com`;

-- スキーマの業務コメント（Genie / Discover が読む）
COMMENT ON SCHEMA `rongzi_catalog_dev`.`master_core`  IS '全社マスタ（Silver）。SKU・商品カテゴリ・製品側標準原価。特定部門が所有しない企業マスタ。hub キー sku_id の出所。SKU はブランド（marketing_core.brand）を参照する。';
COMMENT ON SCHEMA `rongzi_catalog_dev`.`sales_core`   IS '営業（Silver）。受注・請求・営業担当・営業地域・店頭実売（Nielsenパネル）・配下店舗・得意先。hub キー account_id の出所。受注は order_line を持たないヘッダ粒度。受注はキャンペーン（marketing_core.campaign）を参照する。';
COMMENT ON SCHEMA `rongzi_catalog_dev`.`finance_core` IS '財務（Silver）。売掛請求（純売上の正本）・買掛請求・勘定・原価センター・利益センター・財務側標準原価。金額は JPY 建て。';
COMMENT ON SCHEMA `rongzi_catalog_dev`.`trade_core`   IS '販促（Silver）。営業部門の中の販促機能。販促イベント・明細・精算・ファンド・引当・控除。精算と控除は売上のマイナス要素であり売上そのものではない。金額は JPY 建て。';
COMMENT ON SCHEMA `rongzi_catalog_dev`.`marketing_core` IS 'マーケティング（Silver）。ブランド・キャンペーン・媒体費・配信執行・消費者調査・Nielsen syndicated 市場データ。【重要】金額列はすべて USD 建て（currency_code 列を参照）。営業・財務・販促は JPY 建てなので、換算せずに足したり割ったりはできない。consumer_insight は調査費でありキャンペーン投下額ではない。syndicated_market_data.dollar_sales は競合を含む市場全体の売上で、自社の店頭実売（sales_core.pos_transaction）ではない。';
COMMENT ON SCHEMA `rongzi_catalog_dev`.`procure_core` IS '調達（Silver）。発注・サプライヤ。発注金額は仕入であり売上ではない（同名の measure を持つため混同されやすい）。';
COMMENT ON SCHEMA `rongzi_catalog_dev`.`master_mart`   IS '全社マスタの分析層（Gold）。製品標準原価の metric view。';
COMMENT ON SCHEMA `rongzi_catalog_dev`.`sales_mart`    IS '営業の分析層（Gold）。受注・請求・得意先・営業担当の metric view と、営業成績・得意先カバレッジのマート。';
COMMENT ON SCHEMA `rongzi_catalog_dev`.`finance_mart`  IS '財務の分析層（Gold）。売掛請求（純売上の正本）・買掛請求の metric view と、売上照合・標準原価比較のマート。';
COMMENT ON SCHEMA `rongzi_catalog_dev`.`trade_mart`    IS '販促の分析層（Gold）。販促イベント・明細・精算・ファンド・引当の metric view と、販促ROI・販促費フローのマート。';
COMMENT ON SCHEMA `rongzi_catalog_dev`.`marketing_mart` IS 'マーケティングの分析層（Gold）。キャンペーン実績・媒体費・消費者調査の metric view と、キャンペーン実績・ブランド市場ポジション・媒体効率のマート。金額は USD 建て。';
COMMENT ON SCHEMA `rongzi_catalog_dev`.`procure_mart`  IS '調達の分析層（Gold）。発注の metric view。発注額は売上ではない。';
COMMENT ON SCHEMA `rongzi_catalog_dev`.`xdept_mart`    IS '部門横断マート（Gold）。「売上」と呼ばれる5つの数字を並べた mart_revenue_definitions、「マーケに使ったお金」と呼ばれる5つを並べた mart_spend_definitions、得意先軸で部門を結合した mart_customer_360、ブランド別の投資対効果 mart_brand_investment_return。';
COMMENT ON SCHEMA `rongzi_catalog_dev`.`semantics_ops` IS '定義衝突の検出結果・Page ドラフト・認定台帳・オントロジー実行ログ。業務ユーザーには見せない。';
COMMENT ON SCHEMA `rongzi_catalog_dev`.`platform_ops`  IS 'パイプライン実行ログ・expectations 結果・鮮度・Grant スナップショット。業務ユーザーには見せない。';
