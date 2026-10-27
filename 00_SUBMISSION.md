# Brickshouse Food and Beverage — Genie One をもっとよく使うためのツール

**提出者**: Rongzi Yan / **業界**: CPG（食品・飲料）/ **データ**: 全て合成（顧客データなし）

---

## 1. 顧客課題

> **全社に Genie One を配ったら、部門ごとに「売上」の意味が違って数字が合わず、誰も答えを信用しなくなった。**

仮想の課題ではない。Databricks 公式の
[Industry Data Model (Food & Beverage ECM)](https://github.com/databricks-industry-solutions/lakehouse-industry-data-models/tree/main/data-models/food_beverage/v1)
を入れた**時点で**起きる。**衝突は仕込んでいない。ECM に素で存在するものを使った。**

| # | 同じ名前 | 片方 | もう片方 | 倍率 |
|---|---|---|---|---|
| ① | `total_net_amount` | `ar_invoice` 純売上 **1,286億円（正本）** | 受注1,573億 / 発注598億 / 買掛530億 / 販促精算107億 | **15倍** |
| ② | `total_actual_spend_usd` | `campaign` マーケ投下額 **$54.2M** | `consumer_insight` 調査費 $2.9M | **18倍** |
| ③ | （金額一般） | マーケ = **USD** | 営業・財務・販促 = **JPY** | **150倍** |
| ④ | `dollar_sales` | `pos_transaction` 自社店頭実売 33.0億円 | `syndicated_market_data` 市場全体 $121億 | **550倍** |

→ 証跡 [`evidence/04_definition_conflict.md`](evidence/04_definition_conflict.md)

### そして実機で最悪のケースが起きた（2026-10-26 実測）

Genie One に **「売上」** と1語入れたところ、**アカウントに既にあった他人の Page 4件**
（`純売上` / `Net Revenue` / `Net Sales` / `Total Revenue`）を引き、その Page に書かれた
テーブル名を探して **`samples.bakehouse.sales_transactions`（ベーカリーのサンプルデータ）で
「売上 66,471」** と答えた。**Brickshouse のデータを1行も見ていない。**

**Page を置かないと、AI は社内のどこかにある別の用語集で答える。** これが本当の痛み。

---

## 2. 作ったもの

Genie One は使う製品であって作る対象ではない。作ったのは**答えを出せる状態にする工程**。

```
metric view の YAML / 列コメント / データの実測値
   │
   ├─ 検出 ──→ 同名 measure を機械的に洗い出し、MEASURE() で実測し、LLM が業務語を付ける
   ├─ ML ───→ 82グループのレビュー行列を並べ替える（ラベルは人の判断）
   ├─ App ──→ 各部門の定義と実測値を並べ、用語と正本を人が決める
   ├─ Lakebase → 判断を永続化。却下は再提案しない制約として読み戻す ─┐
   │                                              └─ ML の学習ラベル ─┘
   └─ 認定・Page・Agent 命令 → Genie One の答えが変わる → 49問で測る
```

**どれか1つ抜くとループが壊れる。** これが Lakebase / App / ML が必要な理由。

---

## 3. 必須6コンポーネントの充当

| # | 必須 | 実装 | 証跡 |
|---|---|---|---|
| 1 | **Lakeflow** | SDP 3層。`ops_landing` **30 STREAMING TABLE**（`read_files`・ソースシステム単位）→ `*_core` **30 MATERIALIZED VIEW**（**PK 30 / FK 78 / expectations 40 をパイプライン定義で宣言**）→ `*_mart` / `xdept_mart` **13 MV** | [`02_lakeflow.md`](evidence/02_lakeflow.md) |
| 2 | **Unity Catalog** | **1,190列**の業務コメント（ECM由来・値域つき）・PK/FK・**ドメイン1＋subdomain 2**（営業/財務）・資産59個へのドメインタグ・認定・**metric view 16** | [`03_unity_catalog.md`](evidence/03_unity_catalog.md) |
| 3 | **Lakebase** | 衝突の承認/却下/正本選択を永続化。**却下ペアを次回検出の制約として読み戻す**（ループの折り返し点）。9テーブル＋1ビュー | [`06_lakebase.md`](evidence/06_lakebase.md) |
| 4 | **ML / GenAI** | **GenAI** = 衝突に業務語と根拠文を付ける（`ai_query`）。**ML** = 82グループのレビュー行列のランキング。**交差検証 PR-AUC 0.955 / 上位16件の適合率100%**（母比率33%・ベースライン最良0.675）。UC 登録済 | [`07_ml.md`](evidence/07_ml.md) |
| 5 | **Genie Agent** | 部門別4本（営業30表（販促含む） / 財務15 / マーケ15 / 横断18）。**統治OFF では横断マートを外す** | `06_genie/` |
| 6 | **Databricks App** | 3画面（① ペルソナ別の問い ② 衝突レビュー→Lakebase→MLラベル ③ 統治効果 before/after）。React+Vite+FastAPI | `09_app/` |

**＋ AI/BI ダッシュボード3本**（営業/財務/マーケ・公開済み）。存在自体が inferred ontology への入力になる。
→ [`11_dashboards.md`](evidence/11_dashboards.md)

---

## 4. 結果 — 同じ49問を、統治前と統治後に聞いた

| | 統治前 | 統治後 | 差 |
|---|---|---|---|
| 全体 正答率 | 31/49 (63%) | **41/49 (84%)** | **+21 pt** |
| 全体 正本参照率 | 27/49 (55%) | **36/49 (73%)** | +18 pt |
| **衝突ありの問い 21問** | 8/21 (**38%**) | 18/21 (**86%**) | **+48 pt** |
| **衝突ありの正本参照率** | 4/21 (**19%**) | 12/21 (**57%**) | **+38 pt** |
| **衝突なしの問い 28問** | 23/28 (**82%**) | 23/28 (**82%**) | **±0** |
| 罠を踏んだ | 2件 | **0件** | −2 |
| 聞き返し・拒否 | 5件 | **0件** | −5 |
| 部門別（横断 / マーケ） | 29% / 67% | **86% / 100%** | |

**主張の核は「衝突なしが 82% のまま1問も動かなかった」こと。**
統治は定義が割れる問いだけを 38%→86% に動かし、それ以外には触っていない。
「全体的に良くなった」ではなく**「狙ったものだけが直った」**ことの証明である。

### 差は誤差ではない

統治後の状態で**同じ49問を繰り返し**測った（計3回・3回目は49問完走）。
**全体の正答率の揺れは 0.0〜3.7 pt。** 2回目は6問の判定が変わったが
**3問が正解に・3問が不正解に動いて相殺し、正答率は1問も動かなかった**（29/37 → 29/37）。
3回目は**正本参照率が 36/49 → 36/49 で完全一致**した。
揺れは方向を持たない。**+21pt は揺れの5.7倍以上、+48pt は13倍以上。**
→ [`10_variance.md`](evidence/10_variance.md)

### 正直に書くこと

- **boolean 4問と explanation 3問は識別力が弱い**（常識とテーブル名で答えられる）。主軸は scalar + ranking 42問
- 残る8問の失敗のうち2問は**質問が曖昧**（「受注推移」に集計単位を書かなかった等）。
  差が大きく見えるように後から書き換えることはしていない
- **ラベルもスコアも私が作った。** 採点器のバグは before 側も after 側も両方向に直した
- **この 41/49 (84%) より後に、統治の欠陥を1つ直している。** 財務の instruction が
  正しい表を指しながら**粒度を書いていなかった**（FI-F-05）。修正後の49問完走は
  **43/49 (88%)** だが、1問だけ測り直して積み増すのは筋が通らないため
  報告値は 84% に据え置く。経緯は `BUILD_LOG.md`「測定後に直した統治の欠陥」
  （boolean の「拒否」と「いいえ」を区別していなかった）。再採点は再実行ではなく
  **保存済みの回答文に対して採点だけをやり直す**ので、変化は修正だけに帰属する

---

## 5. 借りたものと、自分で決めたこと

**借りた**: ECM（19ドメイン / 376テーブル / 13,111属性 / 1,748 FK / 92 metric view）の**意味論** — DDL・列コメント（値域つき）・PK/FK・metric view。**データは1行も含まれない。**

| 判断 | 理由 |
|---|---|
| 376テーブルから **30テーブル1,190列**を選ぶ | 4つの衝突が成立する最小集合。hub キー（account_id / sku_id / brand_id / campaign_id）を死守 |
| **部門をスキーマの第一軸**にした（層ではなく） | 部門ごとに Agent とドメインを切るため。層を第一軸にすると部門が潰れる |
| 列の値域を**ECM の列コメントから機械的に取得**してデータ生成 | 123列に `Valid values are` がある。自作すると意味論が二重管理になる |
| **上書きした列はコメントの値域も上書き**（55列） | 宣言と実データがずれると Genie が辞書を信じて WHERE を間違える（`channel` で実際に 0円を返した） |
| bronze に**汚れを3,379行（1.6%）注入**し、隠さずダッシュボードに出す | 汚れが無いと expectations が0件違反で飾りに見える。品質の問題は見せるのが統治 |
| 横断マートを**統治ONで初めて配る** | 横断マートは統治の成果物。統治前の状態に置くと答えが先に漏れる |
| 他人の Page の語（`Net Sales` 等）を**同義語に書かない** | 書けば勝てるが、他のFEのデモに我々の Page が出る。同じ害は与えない |

**捨てた道**: 当初は営業・生産・財務で衝突を**自分で仕込む**設計だった。ECM を実測したら
同名 measure が素で存在していたので、**仕込まずに使う**設計に切り替えた。
販促は独立部門ではなく営業の中の機能なので営業に統合し、代わりにマーケを入れた。
これで営業 Agent が受注と販促精算を同じ名前で同時に持ち、**部門内で衝突が起きる**ようになった。

---

## 6. 再現手順

```bash
python3 01_model/extract_model.py     # ECM から30テーブル・FK・metric view
python3 02_data/generate.py           # 206,028行（SEED=20261025・汚れ込み）
python3 tools/sync_value_domains.py   # 列コメントの値域を実データに合わせる
python3 03_lakeflow/gen_pipeline.py && databricks pipelines start-update <id> --full-refresh
#   → FK は親の PK 確立後にしか張れないので、通常更新を収束まで繰り返す（実測3〜4パス）
python3 tools/run_sql.py 01_model/metric_views.sql 05_governance/01_tags.sql
python3 05_governance/04_asset_domain_tags.py   # 資産59個へタグ（スキーマからは継承されない）
python3 10_detect/detect_conflicts.py && python3 06_genie/create_agents.py
python3 04_eval/check_truth.py && python3 04_eval/run_eval.py --route --label before
python3 tools/run_sql.py 05_governance/03_governance_on.sql
python3 06_genie/apply_instructions.py && python3 04_eval/run_eval.py --route --label after
python3 04_eval/rescore.py before after && python3 04_eval/variance.py after after2
```

**未完**: Page 22本の投入（**公開APIがまだ無く** Genie Code の Bulk import が唯一の経路。
手順は `07_pages/HOW_TO_IMPORT.md`）。ML serving endpoint はデモ直前に立てる（課金のため）。

---

## 7. ディレクトリ

`01_model` ECM抽出 / `02_data` 生成 / `03_lakeflow` SDP3層 / `04_eval` 評価49問 /
`05_governance` 統治ON・OFF / `06_genie` Agent4本 / `07_pages` Page22本 / `08_lakebase` /
`09_app` App3画面 / `10_detect` 衝突検出 / `11_dashboards` 3本 / `12_ml` ランキング /
`evidence` 証跡 / `tools` 補助 / **`BUILD_LOG.md` 全工程とハマりどころ27件** /
`DEMO_PLAN_V2.md` 顧客デモ設計
