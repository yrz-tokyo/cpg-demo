-- 統治「後」の状態。認定 ＋ 「何でないか」の明記。
--
-- 設計判断: 競合する metric view を非推奨にはしない。
--   ap_invoice も purchase_order も settlement も、それぞれの問いに対しては正しい答えを返す。
--   間違っているのは「売上」という言葉でそれらが選ばれてしまうこと。
--   よって統治は **削除ではなくラベル付け** で行う。
--     ① 正本を認定する（Genie One を組織が保証した資産へ誘導する）
--     ② そっくりさんに「これは売上ではない」と明記する
--     ③ Page で業務語の正本を定義する（別手順）

-- ① 正本の認定
ALTER VIEW  `rongzi_catalog_dev`.`finance_mart`.`finance_ar_invoice`           SET TAGS ('system.certification_status' = 'certified');
ALTER TABLE `rongzi_catalog_dev`.`finance_mart`.`mart_revenue_reconciliation`  SET TAGS ('system.certification_status' = 'certified');
ALTER TABLE `rongzi_catalog_dev`.`xdept_mart`.`mart_revenue_definitions`       SET TAGS ('system.certification_status' = 'certified');
ALTER TABLE `rongzi_catalog_dev`.`xdept_mart`.`mart_customer_360`              SET TAGS ('system.certification_status' = 'certified');

-- ② そっくりさんに「何であって、何でないか」を書く
COMMENT ON VIEW `rongzi_catalog_dev`.`finance_mart`.`finance_ar_invoice` IS
'【Brickshouse 純売上の正本】売掛請求の金額指標。total_net_amount = 請求総額 - 販促値引(trade_discount_amount) - 控除(deduction_amount)。「Brickshouse の売上」「純売上」「計上売上」を聞かれたらこの measure を使う。受注(sales_order)は売上ではなく受注残を含む見込み。';

COMMENT ON VIEW `rongzi_catalog_dev`.`sales_mart`.`sales_order` IS
'【受注の正本。売上ではない】受注（オーダー）の金額指標。total_net_amount は受注の純額で、一部出荷・返品・販促値引・控除の前の数字。純売上より約25%大きい。「売上」を聞かれた場合はこれではなく finance_mart.finance_ar_invoice を使う。営業の着地見込みにはこちらを使う。';

COMMENT ON VIEW `rongzi_catalog_dev`.`finance_mart`.`finance_ap_invoice` IS
'【買掛（仕入）。売上ではない】仕入先への買掛請求の金額指標。total_net_amount という売上と同名の measure を持つが、これは当社が支払う金額であり売上ではない。「売上」を聞かれてこの measure を使ってはならない。原価・仕入分析に使う。';

COMMENT ON VIEW `rongzi_catalog_dev`.`procure_mart`.`procurement_purchase_order` IS
'【発注（仕入）。売上ではない】サプライヤへの発注の金額指標。total_net_amount という売上と同名の measure を持つが、これは仕入であり売上ではない。「売上」を聞かれてこの measure を使ってはならない。原価率の算出に使う。';

COMMENT ON VIEW `rongzi_catalog_dev`.`trade_mart`.`trade_settlement` IS
'【販促精算。売上ではない】得意先への販促費の支払い（精算）の金額指標。total_net_amount という売上と同名の measure を持つが、これは支払いであり売上ではない。売上に対しては ar_invoice の控除(deduction_amount)としてマイナス方向に反映される。二重計上に注意。';

COMMENT ON VIEW `rongzi_catalog_dev`.`trade_mart`.`trade_promotion_event` IS
'販促イベントの計画/実績指標。actual_revenue は販促システム側の自己申告値であり、財務の純売上(finance_ar_invoice)とは一致しない。会社の売上として使ってはならない。販促の効果測定にのみ使う。';


-- ============================================================================
-- マーケ（フェーズ2）。衝突は3組増えた:
--   ② マーケ投下額 vs 消費者調査費（total_actual_spend_usd が完全同名）
--   ③ 通貨（マーケは USD・他部門は JPY）
--   ④ dollar_sales の universe（市場全体 vs 自社の店頭実売）
-- ============================================================================

-- ① 正本の認定
ALTER VIEW  `rongzi_catalog_dev`.`marketing_mart`.`marketing_campaign_performance` SET TAGS ('system.certification_status' = 'certified');
ALTER TABLE `rongzi_catalog_dev`.`marketing_mart`.`mart_campaign_performance`      SET TAGS ('system.certification_status' = 'certified');
ALTER TABLE `rongzi_catalog_dev`.`marketing_mart`.`mart_brand_market_position`     SET TAGS ('system.certification_status' = 'certified');
ALTER TABLE `rongzi_catalog_dev`.`marketing_mart`.`mart_media_efficiency`          SET TAGS ('system.certification_status' = 'certified');
ALTER TABLE `rongzi_catalog_dev`.`xdept_mart`.`mart_spend_definitions`             SET TAGS ('system.certification_status' = 'certified');
ALTER TABLE `rongzi_catalog_dev`.`xdept_mart`.`mart_brand_investment_return`       SET TAGS ('system.certification_status' = 'certified');

-- ② そっくりさんに「何であって、何でないか」を書く
COMMENT ON VIEW `rongzi_catalog_dev`.`marketing_mart`.`marketing_campaign_performance` IS
'【Brickshouse マーケ投下額の正本】キャンペーンの金額指標。total_actual_spend_usd が「マーケ投下額」「広宣費」「マーケに使ったお金」の正本。【単位は USD】営業・財務・販促は JPY 建てなので、換算せずに足したり割ったりしてはならない。換算が必要な集計は xdept_mart.mart_brand_investment_return を使う（換算レートを列に明示してある）。消費者調査費(marketing_consumer_insight)は投下額ではない。';

COMMENT ON VIEW `rongzi_catalog_dev`.`marketing_mart`.`marketing_consumer_insight` IS
'【消費者調査費。マーケ投下額ではない】消費者調査プロジェクトの指標。total_actual_spend_usd という marketing_campaign_performance と完全に同名の measure を持つが、これは調査会社に払った調査費であり、媒体やキャンペーンへの投下額ではない（投下額の約5%）。「マーケ投下額」を聞かれてこの measure を使ってはならない。この表の正しい使い道は avg_nps_score / avg_concept_test_score / avg_sensory_score などの調査結果。';

COMMENT ON VIEW `rongzi_catalog_dev`.`marketing_mart`.`marketing_media_spend` IS
'【媒体費。マーケ投下額の一部】媒体購入の金額・効率指標。total_actual_spend_amount はマーケ投下額の約70%にあたる媒体購入分で、投下額の全部ではない（残りは制作費・代理店フィー）。【単位は USD】。avg_roi_index は Nielsen の指数であって投資回収率ではない（1.2 は「120%回収」ではなく「基準比1.2」）。currency_code が空の明細があるため、集計前に mart_media_efficiency.missing_currency_rows を確認する。';

-- マート（xdept_mart / *_mart の mart_*）への COMMENT ON は書かない。
-- マートは Lakeflow が所有する MV で、定義の中に COMMENT を持っているため、
-- 次のパイプライン実行で上書きされて消える（フェーズ1の#15と同じ罠）。
-- 統治のテキストは「自分が所有しているもの」= metric view と Page に置き、
-- マートに対しては認定タグ（上の SET TAGS）だけを付ける。
-- syndicated_market_data の構造的事実（市場全体・USD・8地域）はパイプライン定義側に置いてある。
