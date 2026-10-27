-- 統治ループの往復テスト
--   検出 → 候補列挙 → 人の判断 → 却下の永続化 → ML ラベルの導出 → 検出器が却下を読み戻す
-- この往復が成立することが、Lakebase が必要な理由（バッチ分析用テーブルでは成立しない）

\echo '--- 1. 検出: 「売上」の衝突を登録 ---'
INSERT INTO semantics.conflict
  (term, term_normalized, measure_name, detector_version, ml_score, evidence)
VALUES
  ('売上', 'uriage', 'total_net_amount', 'detector-0.1.0', 0.9412,
   '{"same_measure_name_in_domains": 4, "value_spread_ratio": 14.85,
     "overlap_on_account_id": 0.98, "grounded_on": "information_schema + metric view YAML"}'::jsonb),
  ('原価', 'genka', 'standard_cost', 'detector-0.1.0', 0.7108,
   '{"same_concept_two_owners": 2, "unit_cost_gap_ratio_p50": 0.061}'::jsonb)
ON CONFLICT (term_normalized, measure_name, detector_version) DO NOTHING;

\echo '--- 2. 候補: 同名 measure を持つオブジェクトを列挙（実測値つき） ---'
INSERT INTO semantics.conflict_candidate
  (conflict_id, object_name, object_type, department, measure_expr, role, observed_value, note)
SELECT c.conflict_id, v.obj, 'METRIC_VIEW', v.dept, v.expr, v.role, v.val, v.note
FROM semantics.conflict c
CROSS JOIN (VALUES
  ('rongzi_catalog_dev.finance_mart.finance_ar_invoice', '財務', 'SUM(net_amount)',
   'authoritative',     127470000000.00, '純売上の正本。請求総額 - 販促値引 - 控除'),
  ('rongzi_catalog_dev.sales_mart.sales_order', '営業', 'SUM(total_net_amount)',
   'variant',           158850000000.00, '受注。一部出荷・値引・控除の前。純売上より約25%大きい'),
  ('rongzi_catalog_dev.procure_mart.procurement_purchase_order', '調達', 'SUM(net_amount)',
   'not_this_concept',   60100000000.00, '発注＝仕入。売上ではない'),
  ('rongzi_catalog_dev.finance_mart.finance_ap_invoice', '財務', 'SUM(net_amount)',
   'not_this_concept',   53230000000.00, '買掛＝仕入。売上ではない'),
  ('rongzi_catalog_dev.trade_mart.trade_settlement', '販促', 'SUM(net_amount)',
   'not_this_concept',   10700000000.00, '販促精算＝得意先への支払い。売上ではない')
) AS v(obj, dept, expr, role, val, note)
WHERE c.term_normalized = 'uriage'
ON CONFLICT (conflict_id, object_name) DO NOTHING;

\echo '--- 3. 人の判断: 「売上」は承認、「原価」は却下 ---'
INSERT INTO semantics.decision (conflict_id, decision, authoritative_object, rationale, decided_by)
SELECT conflict_id, 'approve',
       'rongzi_catalog_dev.finance_mart.finance_ar_invoice',
       '財務・営業・販促の3部門長で合意。会社の売上は純売上とする。受注は着地見込みとして別名で扱う。',
       'rongzi.yan@databricks.com'
FROM semantics.conflict WHERE term_normalized = 'uriage';

INSERT INTO semantics.decision (conflict_id, decision, rationale, decided_by)
SELECT conflict_id, 'reject',
       '製品側原価と財務側原価は目的が違う（開発時の見積り vs 会計上の評価）。衝突ではなく併存が正しい。',
       'rongzi.yan@databricks.com'
FROM semantics.conflict WHERE term_normalized = 'genka';

UPDATE semantics.conflict SET status = 'resolved',
       authoritative_object = 'rongzi_catalog_dev.finance_mart.finance_ar_invoice'
WHERE term_normalized = 'uriage';
UPDATE semantics.conflict SET status = 'rejected' WHERE term_normalized = 'genka';

\echo '--- 4. 却下を永続化（検出器が次回読み戻す制約） ---'
INSERT INTO semantics.rejected_pair
  (term_normalized, measure_name, object_a, object_b, rejected_by, reason)
VALUES ('genka', 'standard_cost',
        'rongzi_catalog_dev.master_mart.product_standard_cost',
        'rongzi_catalog_dev.finance_core.finance_standard_cost',
        'rongzi.yan@databricks.com', '目的が違うため併存が正しい')
ON CONFLICT DO NOTHING;

\echo '--- 5. Page ドラフトを登録 ---'
INSERT INTO semantics.page_draft
  (conflict_id, title, synonyms, definition_md, business_use_md, related_assets, source_assets, generated_by)
SELECT conflict_id, '売上（Brickshouse 全社定義）',
  ARRAY['売上','純売上','計上売上','売上高','revenue','net revenue','受注金額','受注高','店頭消化','sell-out'],
  'Brickshouse の「売上」の正本は finance_mart.finance_ar_invoice の total_net_amount（純売上）。'
  '計算式は 請求総額 - 販促値引(trade_discount_amount) - 控除(deduction_amount)。2026年は約1,274.7億円。',
  '社内には「売上」と呼ばれる数字が5つある。問いが「会社の売上」なら必ず純売上を使う。'
  '受注(1,588.5億)・発注(601.0億)・買掛(532.3億)・販促精算(107.0億)は売上ではない。',
  ARRAY['rongzi_catalog_dev.finance_mart.finance_ar_invoice',
        'rongzi_catalog_dev.xdept_mart.mart_revenue_definitions'],
  ARRAY['rongzi_catalog_dev.finance_core.ar_invoice'],
  'databricks-claude-sonnet-4-5'
FROM semantics.conflict WHERE term_normalized = 'uriage';

\echo '--- 6. 認定台帳 ---'
INSERT INTO semantics.certification (object_name, cert_status, applied_by)
VALUES ('rongzi_catalog_dev.finance_mart.finance_ar_invoice', 'certified', 'rongzi.yan@databricks.com')
ON CONFLICT (object_name) DO UPDATE SET cert_status = EXCLUDED.cert_status, applied_at = now();

\echo ''
\echo '=== 読み戻し: 衝突と判断 ==='
SELECT c.term, c.status, c.ml_score, substr(c.authoritative_object, 20) AS authoritative,
       d.decision, d.decided_by
FROM semantics.conflict c
LEFT JOIN semantics.decision d ON c.conflict_id = d.conflict_id
ORDER BY c.ml_score DESC;

\echo ''
\echo '=== 読み戻し: 「売上」の候補（画面で並べて見せるもの） ==='
SELECT department, role, substr(object_name, 20) AS object,
       to_char(observed_value/1e8, 'FM999990.0') AS oku_yen, substr(note, 1, 40) AS note
FROM semantics.conflict_candidate cc
JOIN semantics.conflict c USING (conflict_id)
WHERE c.term_normalized = 'uriage'
ORDER BY observed_value DESC;

\echo ''
\echo '=== 読み戻し: ML 教師データ（decision から機械的に導出） ==='
SELECT term_normalized, measure_name, label_is_real_conflict,
       evidence->>'value_spread_ratio' AS value_spread_ratio
FROM semantics.ml_training_label ORDER BY label_is_real_conflict DESC;

\echo ''
\echo '=== 読み戻し: 検出器が次回読む「却下済み」制約 ==='
SELECT term_normalized, measure_name, substr(object_a, 20) AS a, substr(object_b, 20) AS b, reason
FROM semantics.rejected_pair;

\echo ''
\echo '=== 読み戻し: Page ドラフト ==='
SELECT title, status, array_length(synonyms, 1) AS n_synonyms,
       array_length(related_assets, 1) AS n_related, generated_by
FROM semantics.page_draft;
