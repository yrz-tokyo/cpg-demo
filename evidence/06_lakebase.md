# 06 Lakebase（統治ループの人間側の状態）

インスタンス `brickshouse` / CU_1 / PG16 / us-east-1

**なぜ Delta テーブルではないのか**
1. 行単位の更新が頻発（1つの衝突の状態が 検出→調査中→正本決定→公開 と何度も書き換わる）
2. 同時更新がある（営業部長と財務部長が別々の行に自分の主張を書く）
3. **read-modify-write がある**（検出バッチが毎回「却下済み」を読んで次の提案から除外）
4. アプリがサブ秒で読み書きする
バッチ分析用のテーブルでは 1〜4 が成立しない。

### 作成したオブジェクト
```
?column?           
------------------------------
 app.annotation
 app.audit_log
 app.bookmark
 semantics.certification
 semantics.conflict
 semantics.conflict_candidate
 semantics.decision
 semantics.ml_training_label
 semantics.page_draft
 semantics.rejected_pair
(10 rows)
```

### 衝突と人の判断（往復の結果）
```
term |  status  | ml_score | decision |        decided_by         
------+----------+----------+----------+---------------------------
 売上 | resolved |   0.9412 | approve  | rongzi.yan@databricks.com
 原価 | rejected |   0.7108 | reject   | rongzi.yan@databricks.com
(2 rows)
```

### 「売上」の候補（レビュー画面に並べる内容）
```
department |       role       |                 object                  | oku_yen 
------------+------------------+-----------------------------------------+---------
 営業       | variant          | sales_mart.sales_order                  |  1588.5
 財務       | authoritative    | finance_mart.finance_ar_invoice         |  1274.7
 調達       | not_this_concept | procure_mart.procurement_purchase_order |   601.0
 財務       | not_this_concept | finance_mart.finance_ap_invoice         |   532.3
 販促       | not_this_concept | trade_mart.trade_settlement             |   107.0
(5 rows)
```

### ML 教師データ（decision から機械的に導出＝ループが閉じている証跡）
```
term_normalized |   measure_name   | label_is_real_conflict | value_spread 
-----------------+------------------+------------------------+--------------
 uriage          | total_net_amount |                      1 | 14.85
 genka           | standard_cost    |                      0 | 
(2 rows)
```

### 検出器が次回読む「却下済み」制約（再提案しないための入力）
```
term_normalized | measure_name  |           reason           
-----------------+---------------+----------------------------
 genka           | standard_cost | 目的が違うため併存が正しい
(1 row)
```
