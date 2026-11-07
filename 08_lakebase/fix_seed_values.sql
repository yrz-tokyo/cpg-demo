-- conflict_id 1（「売上」）の候補値を実測値に合わせる。
--
-- なぜ必要か
--   roundtrip_test.sql が丸めた概算値（純売上 1,274.7億など）をシードしていた。
--   App のレビュー画面はこの値を表示するので、Genie が 1,286.1億 と答える隣に
--   1,274.7億 が出て、デモの最中に矛盾が見える。
--   「用語集に金額を固定で書くな」と同じ問題を、Lakebase 側でも踏んでいた。
--
--   観測値そのもの（observed_value）は「検出時に測った値」なので残す。
--   ただし自由記述の note からは金額を外す。データ更新のたびに嘘になるため。
--
-- 実測日 2026-11-07 / 対象年 2026 / SEED=20261025

BEGIN;

UPDATE semantics.conflict_candidate SET observed_value = 128613230122.32,
       note = '純売上の正本。請求総額 - 販促値引 - 控除'
 WHERE object_name = 'rongzi_catalog_dev.finance_mart.finance_ar_invoice';

UPDATE semantics.conflict_candidate SET observed_value = 157253032520.84,
       note = '受注。一部出荷・値引・控除の前なので純売上より大きい'
 WHERE object_name = 'rongzi_catalog_dev.sales_mart.sales_order';

UPDATE semantics.conflict_candidate SET observed_value = 59831718576.37
 WHERE object_name = 'rongzi_catalog_dev.procure_mart.procurement_purchase_order';

UPDATE semantics.conflict_candidate SET observed_value = 53008284375.74
 WHERE object_name = 'rongzi_catalog_dev.finance_mart.finance_ap_invoice';

UPDATE semantics.conflict_candidate SET observed_value = 10645420612.49
 WHERE object_name = 'rongzi_catalog_dev.trade_mart.trade_settlement';

-- Page ドラフトの同義語を実際の Page 1 と揃える。
--   元は 'net revenue' を含んでいた。これは他FEの Page が使っている語で、
--   奪うと相手のデモに我々の Page が出るため、意図的に使わないと決めている。
--   受注・店頭実売の語も混ざっていた（1つの語の持ち主は1つの Page だけ）。
UPDATE semantics.page_draft SET
  synonyms = ARRAY['売上','Brickshouse の売上','Brickshouse の純売上','純売上','計上売上',
                   '認識売上','売上高','財務の売上','Brickshouse revenue',
                   'Brickshouse net sales','トップライン'],
  definition_md = 'Brickshouse の「売上」の正本は finance_mart.finance_ar_invoice の '
                  'total_net_amount（純売上）。計算式は 請求総額 - 販促値引(trade_discount_amount) '
                  '- 控除(deduction_amount)。金額は Genie が毎回集計する（用語集に固定で書かない）。',
  business_use_md = '社内には「売上」と呼ばれる数字が5つある。問いが「会社の売上」なら必ず純売上を使う。'
                    '受注・発注・買掛・販促精算・店頭実売は売上ではない。'
 WHERE title = '売上（Brickshouse 全社定義）';

COMMIT;

\echo '--- 修正後の conflict_id 1 の候補 ---'
SELECT object_name, observed_value::numeric(20,2), role, note
  FROM semantics.conflict_candidate
 WHERE conflict_id = 1 ORDER BY observed_value DESC;

\echo '--- page_draft の同義語に net revenue が残っていないか（0 なら OK）---'
SELECT count(*) AS net_revenue_が残っている件数
  FROM semantics.page_draft WHERE 'net revenue' = ANY(synonyms);
