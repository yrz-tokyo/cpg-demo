# ワークスペース命令（コピペ用）

## どこに貼るか — UI の設定画面は無い。**ワークスペースのファイル**として置く

```
/Workspace/.genie_workspace_instructions.md
```

**設定ペインを探しても見つからない。** Genie One の「カスタマイズ」は外観
（色・ロゴ・ウェルカム文・ピン留め）だけで、命令の欄は無い。
命令は上のパスに Markdown ファイルを置くだけで、**追加設定は不要**（Chat が自動で読む）。

docs（`genie-one/chat`）の記述:
> Workspace admins can add custom instructions that apply to every chat conversation in the workspace.
> Instructions must be under 20,000 characters.
> Instructions apply to chat only and do not affect Genie Agents or Genie Code.

**投入済み**（2026-10-27・1,650文字）。CLI で置いた:

```bash
databricks workspace import "/Workspace/.genie_workspace_instructions.md" \
  --file <ローカルのファイル> --format RAW --overwrite
```

### 紛らわしい別物に注意

`.assistant_workspace_instructions.md`（`.genie_` ではなく `.assistant_`）という
**よく似た名前のファイルがあるが、これは Genie Code 用**で Genie One の Chat には効かない。
一度こちらに置いてしまい、消して置き直した。

このワークスペース（`fevm-serverless-rongzi-cpg-general`）にしか効かない。
Page はアカウント共有で他FEの Page と競合するが、**ワークスペース命令は他者に漏れない**ので、
他人のデモを壊さずに強く誘導できる唯一の手段。

**Genie Agent には効かない。** Agent 側は `06_genie/apply_instructions.py` が別に入れている。

## 注意: Agent への誘導は効かないかもしれない

文面に「部門ごとの Agent を使ってください」と書いてあるが、**これは未検証**。
2026-10-26 の実機では Genie One は **Agent に自動ルーティングしなかった**
（オントロジー検索とテーブル検索で完結し、Agent を一度も使わなかった）。
効けば得・効かなくても害はないので残しているが、
**デモでは Agent を自分で選ぶ前提にすること。**
「言えば Agent に行く」を筋書きに組み込むと本番で外れる。

---

## 置いた文面（ファイルの中身）

```
このワークスペースは Brickshouse Food and Beverage（ビール類・清涼飲料・健康食品の
3事業を持つ日本の CPG 企業）専用です。データはすべてカタログ `rongzi_catalog_dev` にあります。

【絶対に守ること】
- `samples` カタログ（bakehouse / nyctaxi / tpch など）を使ってはいけません。
  このワークスペースの業務データではありません。
- 用語集（オントロジー / Page）を参照するときは、タイトルに「Brickshouse」が付いた
  Page だけを使ってください。他社・他部門の同名 Page（純売上 / Net Revenue / Net Sales /
  Total Revenue など）は Brickshouse の定義ではありません。
- 答えには必ず、使ったテーブル名（カタログ・スキーマ込み）を書いてください。

【部門ごとの Genie Agent を使ってください】
部門が特定できる質問は、まず該当する Agent に聞いてください。
- 営業・販促の質問 → 「Brickshouse 営業」
- 財務・経理の質問 → 「Brickshouse 財務」
- マーケティングの質問 → 「Brickshouse マーケティング」
- 部門をまたぐ質問 → 「Brickshouse 全社横断」

【「売上」と言われたら】
Brickshouse では部門ごとに違う数字を「売上」と呼んでいます。どれを聞かれているか
曖昧なときは、`rongzi_catalog_dev.xdept_mart.mart_revenue_definitions` で5つを並べ、
どれが正本かを明示してください。
- 純売上（会社の正本・財務）= `finance_core.ar_invoice.net_amount`。2026年は約1,286億円
- 受注（営業の着地見込み）= `sales_core.order.total_net_amount`。約1,573億円。会社の売上ではない
- 発注（調達）= `procure_core.purchase_order.net_amount`。約598億円
- 販促精算（販促）= `trade_core.settlement.net_amount`。約107億円。売上のマイナス要素
- 店頭実売（POS投影値）= `sales_core.pos_transaction.dollar_sales`。約33億円。絶対額で比較しない

【通貨】
マーケティング（`marketing_core` / `marketing_mart`）は USD 建て。営業・財務・販促は JPY 建て。
換算せずに足すと150倍ずれます。足す必要があるときは換算レートを答えに書いてください。
換算済みの集計は `xdept_mart.mart_brand_investment_return` にあります。

【取り違えが多い列】
- `dollar_sales` は2つあります。`sales_core.pos_transaction` = 自社・JPY・パネル投影値、
  `marketing_core.syndicated_market_data` = 市場全体・USD・競合込み。約550倍違います。
- 「マーケ投下額」は `marketing_mart.marketing_campaign_performance`。
  消費者調査費（`marketing_consumer_insight`）と媒体費（`marketing_media_spend`）は別物です。
- 原価率 = 発注 ÷ 純売上（2026年は約47%）。受注を分子にしてはいけません。
- 得意先名は「<社名> <地域>支社」の形です。社名だけでは一意になりません。
```

---

## 貼った後の確認

Genie One で **「売上」** と1語だけ入れて、`samples.bakehouse` を引かなくなったことを見る。
Page 投入前でもこの命令だけで改善するはずで、**Page を入れるとさらに引用元が Page になる**。
