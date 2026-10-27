# Brickshouse Food and Beverage — 業務用語集（Page の原稿）

すべて UC ドメイン **`Brickshouse Food and Beverage`** に置く。
アカウントのドメイン枠が上限（1000/1000）で subdomain を作れないため、**部門はタイトルと同義語で識別**する。
これは妥協ではなく retrieval 上有利 — 部門名が固有名詞として効き、同業55件の他社ドメインの Page に勝ちやすい。

書き方の規約
- 全社語（部門間で衝突する語）: `<語>（Brickshouse 全社定義）` / 同義語に**各部門の呼び方を全部**入れる
- 部門語: `<語>（Brickshouse <部門>）` / 同義語にその部門の言い回し

**同義語の2つの鉄則**（実機で Genie One を試して分かった）

1. **自分の Page 同士で同じ語を取り合わない。** 同じ語を2つの Page に書くと、こちらの信号が
   分散して、アカウントに既にある他人の Page に負ける。1つの語の持ち主は1つの Page だけ。

2. **他人の Page が使っている語を奪わない。** このアカウントには既に
   `純売上` / `Net Revenue` / `Net Sales` / `Total Revenue` という他FEの Page があり、
   「売上」と聞いた Genie One はそれを引いて `samples.bakehouse.sales_transactions` で答えた。
   同義語に `Net Sales` などを書けば我々が勝つが、**他の人のデモに我々の Page が出る**ようになる。
   同じ害を相手に与えることになるのでやらない。
   代わりに **ワークスペース命令**（このワークスペースにしか効かず他者に漏れない）で強く誘導し、
   Page 側は `Brickshouse` という固有名詞・認定・使用頻度・鮮度で勝つ。

---

## 1. 売上（Brickshouse 全社定義）

**同義語**: 売上, Brickshouse の売上, Brickshouse の純売上, 純売上, 計上売上, 認識売上, 売上高, 財務の売上, Brickshouse revenue, Brickshouse net sales, トップライン

（`Net Revenue` `Net Sales` `Total Revenue` は**あえて入れない**。このアカウントの他FEの Page が
その語を使っており、奪うと相手のデモにこの Page が出てしまう。→ 冒頭の鉄則2）

**Definition**
Brickshouse の「売上」の正本は **`rongzi_catalog_dev.finance_mart.finance_ar_invoice` の `total_net_amount`（純売上）** とする。
計算式は `純売上 = 請求総額(gross_amount) − 販促値引(trade_discount_amount) − 控除(deduction_amount)`。
2026年の値は約 **1,274.7億円**。

**Business use**
社内には「売上」と呼ばれる数字が5つある。問いが「会社の売上」なら必ず純売上を使う。

| 呼ばれ方 | 実体 | 2026年 | 売上か |
|---|---|---|---|
| 純売上・計上売上 | `finance_mart.finance_ar_invoice.total_net_amount` | 1,274.7億 | **これが正本** |
| 受注・受注高 | `sales_mart.sales_order.total_net_amount` | 1,588.5億 | 売上ではない（一部出荷・値引・控除の前） |
| 発注 | `procure_mart.procurement_purchase_order.total_net_amount` | 601.0億 | 売上ではない（仕入） |
| 買掛 | `finance_mart.finance_ap_invoice.total_net_amount` | 532.3億 | 売上ではない（仕入） |
| 販促精算 | `trade_mart.trade_settlement.total_net_amount` | 107.0億 | 売上ではない（得意先への支払い） |
| 店頭実売 | `sales_core.pos_transaction.dollar_sales` | 33.2億 | 売上ではない（Nielsenパネルの投影値・絶対額比較不可） |

**なぜ紛らわしいか**: 業界標準データモデル(ECM)の metric view は、この5つすべてに `total_net_amount` という**完全に同じ名前の measure** を持つ。名前だけでは区別できない。

**Related assets**: `rongzi_catalog_dev.finance_mart.finance_ar_invoice`, `rongzi_catalog_dev.finance_mart.mart_revenue_reconciliation`, `rongzi_catalog_dev.xdept_mart.mart_revenue_definitions`
**Sources**: `rongzi_catalog_dev.finance_core.ar_invoice`

---

## 2. 原価（Brickshouse 全社定義）

**同義語**: 原価, 標準原価, 単位原価, standard cost, unit cost, 製造原価, 売上原価, 原価率

**Definition**
単位原価の正本は **`finance_core.finance_standard_cost.standard_price_per_unit`（財務側標準原価）**。
製品側にも `master_core.product_standard_cost.total_standard_cost_per_unit` があり、**両者は一致しない**。
原価率は `発注金額(procure_mart.procurement_purchase_order.total_net_amount) ÷ 純売上`。2026年は約 **47%**。

**Business use**
製品側原価は開発・設計時の見積り、財務側原価は会計上の評価に使う。
食い違いを見るときは `finance_mart.mart_standard_cost_compare` を使う（両者を並べて差分を出してある）。

**Related assets**: `rongzi_catalog_dev.finance_mart.mart_standard_cost_compare`, `rongzi_catalog_dev.master_mart.product_standard_cost`
**Sources**: `rongzi_catalog_dev.finance_core.finance_standard_cost`, `rongzi_catalog_dev.master_core.product_standard_cost`

---

## 3. 得意先（Brickshouse 全社定義）

**同義語**: 得意先, 顧客, 取引先, アカウント, account, customer, 販売先, チェーン, 小売

**Definition**
`sales_core.account` が得意先マスタの正本。`account_id` が営業・財務・販促を貫く hub キー。
`channel` は SM / CVS / DgS / 卸 / EC の5区分。地域は `shipping_state`。

**Business use**
得意先を軸に3部門を横断して見るときは `xdept_mart.mart_customer_360` を使う（受注・純売上・未回収・販促費・精算・控除・店頭実売が1行に揃っている）。

**Related assets**: `rongzi_catalog_dev.xdept_mart.mart_customer_360`, `rongzi_catalog_dev.sales_mart.customer_account_overview`
**Sources**: `rongzi_catalog_dev.sales_core.account`

---

## 4. 商品（Brickshouse 全社定義）

**同義語**: 商品, 製品, SKU, 品目, product, item, 品番, 商品コード

**Definition**
`master_core.sku` が商品マスタの正本。`sku_id` が hub キー。
`product_line` が事業区分（ビール類 / 清涼飲料 / 健康食品）、`flavor_variety` が銘柄。
**注意**: `sales_core.order` は受注ヘッダ粒度で `sku_id` を持たない。商品軸の分析は
`pos_transaction`（店頭実売）・`distribution_point`（配下）・`promotion_line`（販促明細）で行う。

**Related assets**: `rongzi_catalog_dev.master_core.sku`, `rongzi_catalog_dev.master_core.category`
**Sources**: `rongzi_catalog_dev.master_core.sku`

---

## 5. 受注（Brickshouse 営業）

**同義語**: 受注, 受注高, 受注金額, オーダー, order, 受注残, 営業の売上, 着地見込み

**Definition**
`sales_mart.sales_order.total_net_amount`。`総額(total_gross_amount) − 値引(total_discount_amount)`。
2026年は約 **1,588.5億円**で、純売上より約 **25%大きい**。

**Business use**
営業の着地見込みにはこれを使う。**「会社の売上」として使ってはならない**。
差が出る理由は 一部出荷・返品・販促値引・控除。差の内訳は `xdept_mart.mart_revenue_definitions` に月次で入っている。

**Related assets**: `rongzi_catalog_dev.sales_mart.mart_sales_performance`, `rongzi_catalog_dev.xdept_mart.mart_revenue_definitions`
**Sources**: `rongzi_catalog_dev.sales_core.order`

---

## 6. 配下率（Brickshouse 営業）

**同義語**: 配下率, 配荷率, ACV, ACV加重配下, TDP, numeric distribution, 取扱率, 棚取り

**Definition**
`sales_core.distribution_point.acv_weighted_distribution_pct`（ACV加重配下率）。
出所は Nielsen の syndicated データ。`numeric_distribution_pct` は店舗数ベース、`tdp_contribution_pct` は TDP 寄与。

**Business use**
棚取りの進捗を見る指標。集計済みは `sales_mart.mart_account_coverage`。
前期比の増減は `acv_change_pct`。

**Related assets**: `rongzi_catalog_dev.sales_mart.mart_account_coverage`
**Sources**: `rongzi_catalog_dev.sales_core.distribution_point`

---

## 7. 店頭実売（Brickshouse 営業）

**同義語**: 店頭実売, 店頭消化, sell-out, POS, スキャンデータ, 実売, 消化

**Definition**
`sales_core.pos_transaction.dollar_sales`。出所は **Nielsen の syndicated パネルで、全店 census ではなく約15% ACV の投影値**。

**Business use**
**当社の売上（sell-in）と絶対額で比較してはならない。** 2026年のパネル値は33.2億円だが、これは
純売上1,274.7億円の一部を投影したものに過ぎない。比較は**伸び率・指数**で行う。
sell-in と sell-out の乖離を見る目的（棚の消化不足・過剰出荷の検知）に使う。

**Sources**: `rongzi_catalog_dev.sales_core.pos_transaction`

---

## 8. 売上計上のタイミング（Brickshouse 財務）

**同義語**: 売上計上, 計上タイミング, 収益認識, revenue recognition, 計上月, 計上日, 期ズレ, カットオフ

**Definition**
Brickshouse の売上が**いつの月に立つか**は `finance_core.ar_invoice.revenue_recognition_date` で決まる。
請求日（`invoice_date`）とは別の列で、月末前後の請求は計上月がずれることがある。
金額の定義そのものは Page「売上（Brickshouse 全社定義）」を参照する。**この Page は金額ではなく時点を扱う。**

**Business use**
- 月次の着地を見るときは `revenue_recognition_date` で切る。`invoice_date` で切ると期ズレ分が混ざる
- 受注 → 請求 → 計上 の各段の差は `finance_mart.mart_revenue_reconciliation` に並べてある
- 受注日（`order.placed_timestamp`）と計上日は最大で1か月以上離れることがある。
  「営業の着地」と「財務の計上」が食い違う理由の半分はこの時点の違い

**なぜ分けてあるか**: 「売上はいくら」と「売上はいつ立つ」は別の問い。
同じ Page に両方を書くと、金額を聞かれたときに計上日の説明が混ざる。

**Related assets**: `rongzi_catalog_dev.finance_mart.mart_revenue_reconciliation`, `rongzi_catalog_dev.xdept_mart.mart_revenue_definitions`
**Sources**: `rongzi_catalog_dev.finance_core.ar_invoice`

---

## 9. レベニューリーケージ（Brickshouse 財務）

**同義語**: レベニューリーケージ, 売上の漏れ, revenue leakage, 値引・控除, 販促による目減り

**Definition**
`finance_core.ar_invoice` の `trade_discount_amount + deduction_amount`。
請求したのに純売上にならなかった金額。2026年は約 **75億円**（純売上の5.9%）。

**Business use**
**未回収売掛（`open_amount`）とは別物。** 未回収は「回収できていない」、リーケージは「そもそも請求額から引かれた」。
得意先別は `xdept_mart.mart_customer_360.revenue_leakage_amount` / `leakage_ratio`。
原因の内訳は `trade_core.deduction.deduction_type`。

**Related assets**: `rongzi_catalog_dev.xdept_mart.mart_customer_360`, `rongzi_catalog_dev.trade_mart.mart_trade_spend_flow`
**Sources**: `rongzi_catalog_dev.finance_core.ar_invoice`, `rongzi_catalog_dev.trade_core.deduction`

---

## 10. 販促費（Brickshouse 販促）

**同義語**: 販促費, 販促, トレードスペンド, trade spend, プロモーション費, 販促投資

**Definition**
`trade_mart.trade_promotion_event.promotional_spend_net`。2026年は約 **146.9億円**（純売上の11.5%）。

**Business use**
ROI は `trade_mart.mart_promotion_roi`。
**注意**: `promotion_event.actual_revenue` は**販促システム側の自己申告値**であり、財務の純売上とは一致しない。
会社の売上として使ってはならない。販促の効果測定にのみ使う。

**Related assets**: `rongzi_catalog_dev.trade_mart.mart_promotion_roi`, `rongzi_catalog_dev.trade_mart.mart_trade_spend_flow`
**Sources**: `rongzi_catalog_dev.trade_core.promotion_event`

---

## 11. 販促精算（Brickshouse 販促）

**同義語**: 販促精算, 精算, settlement, クレーム精算, 販促支払, リベート精算

**Definition**
`trade_mart.trade_settlement.total_net_amount`。得意先からの請求（claim）に対する当社の支払い。
`net_amount = original_claim_amount + adjustment_amount`。2026年は約 **107.0億円**。

**Business use**
**売上ではない。** `total_net_amount` という売上と同名の measure を持つため混同されやすい。
売上に対しては `ar_invoice` の `deduction_amount` としてマイナス方向に反映される。
精算額を売上に足すと**二重計上**になる。

**Sources**: `rongzi_catalog_dev.trade_core.settlement`

---

## 12. 控除（Brickshouse 販促）

**同義語**: 控除, ディダクション, deduction, チャージバック, 差し引き, 減額

**Definition**
`trade_core.deduction.net_amount`。得意先が支払時に差し引いてくる金額。
`deduction_type` は promotion / shortage / damage / pricing / return。2026年は約 **72.3億円**。

**Business use**
`ar_invoice.deduction_amount` に反映され、純売上を押し下げる。
係争中（`dispute_flag`）のものは回収交渉の対象。

**Sources**: `rongzi_catalog_dev.trade_core.deduction`

---

## 13. 発注（Brickshouse 調達）

**同義語**: 発注, 購買, 仕入, purchase order, PO, 調達金額

**Definition**
`procure_mart.procurement_purchase_order.total_net_amount`。2026年は約 **601.0億円**。

**Business use**
**売上ではない。** `total_net_amount` という売上と同名の measure を持つが、当社が支払う金額。
原価率の算出（発注 ÷ 純売上 = 約47%）に使う。
`finance_mart.finance_ap_invoice`（買掛・532.3億円）も同様に売上ではない。

**Sources**: `rongzi_catalog_dev.procure_core.purchase_order`, `rongzi_catalog_dev.finance_core.ap_invoice`

---

## 14. チャネル（Brickshouse 全社定義）

**同義語**: チャネル, 業態, channel, 販路, 取引形態

**Definition**
`sales_core.account.channel` の5区分。
- **SM** スーパーマーケット
- **CVS** コンビニエンスストア
- **DgS** ドラッグストア
- **卸** 酒類・食品卸
- **EC** 自社オンラインを含む電子商取引

**Business use**
受注・純売上・販促費の構成比を見る標準軸。`order.channel` と `pos_transaction.store_format` も同じ区分。

**Sources**: `rongzi_catalog_dev.sales_core.account`

---

## 15. マーケ投下額（Brickshouse マーケ）

**同義語**: マーケ投下額, マーケティング投下額, マーケ費, マーケティング費用, 広宣費, 広告宣伝費, 投下額, marketing spend, media investment, A&P, ATL費用, キャンペーン費用

**Definition**
「マーケ投下額」の正本は **`rongzi_catalog_dev.marketing_mart.marketing_campaign_performance` の `total_actual_spend_usd`**（＝ `marketing_core.campaign.actual_spend_usd` の合計）とする。
**単位は USD。** 2026年の値は約 **$54.2M（1USD=150JPYで約81.3億円）**。
内訳は媒体費（約70%）＋制作費・代理店フィー等。

**Business use**
「マーケにいくら使ったか」はこの数字で答える。以下は**投下額ではない**。

| 呼ばれ方 | 実体 | 2026年 | 投下額か |
|---|---|---|---|
| マーケ投下額・広宣費 | `marketing_mart.marketing_campaign_performance.total_actual_spend_usd` | $54.2M | **これが正本** |
| 消費者調査費 | `marketing_mart.marketing_consumer_insight.total_actual_spend_usd` | $2.9M | **投下額ではない**（調査プロジェクトの費用・約18分の1） |
| 媒体費 | `marketing_mart.marketing_media_spend.total_actual_spend_amount` | $37.5M | 投下額の**一部**（媒体の購入分だけ） |
| 執行実績 | `marketing_core.campaign_execution.actual_spend_amount` | $45.6M | 投下額の明細（campaign_id でロールアップする。二重計上しない） |
| 年間予算 | `marketing_core.brand.annual_marketing_budget` | — | 実績ではなく**予算** |
| 販促費 | `trade_core.promotion_line.total_funding_amount` | **JPY建て** | 営業部門の販促。マーケ投下とは別勘定。**通貨が違うので足す前に換算する** |

**なぜ紛らわしいか**: 業界標準データモデル(ECM)の metric view は、`campaign` と `consumer_insight` の**両方に `total_actual_spend_usd` という完全に同じ名前の measure** を持つ。名前だけでは区別できず、調査費を選ぶと約18分の1になる。

**Related assets**: `rongzi_catalog_dev.marketing_mart.marketing_campaign_performance`, `rongzi_catalog_dev.marketing_mart.mart_campaign_performance`, `rongzi_catalog_dev.xdept_mart.mart_spend_definitions`
**Sources**: `rongzi_catalog_dev.marketing_core.campaign`

---

## 16. 通貨（Brickshouse 全社定義）

**同義語**: 通貨, 建値, 為替, currency, USD, ドル建て, 円建て, JPY, 換算, 為替レート, FX

**Definition**
Brickshouse のデータは**部門によって建値が違う**。

| 部門 / スキーマ | 建値 | 根拠列 |
|---|---|---|
| 営業 `sales_core` / `sales_mart` | **JPY** | `order.currency_code` = 'JPY' |
| 財務 `finance_core` / `finance_mart` | **JPY** | `ar_invoice.currency_code` |
| 販促 `trade_core` / `trade_mart` | **JPY** | `promotion_line.currency_code` |
| **マーケ `marketing_core` / `marketing_mart`** | **USD** | `campaign.currency_code` = 'USD' / `media_spend.currency_code` / `campaign_execution.spend_currency_code` |
| 市場データ `marketing_core.syndicated_market_data` | **USD** | Nielsen の元データが USD |

**Business use**
- **マーケの金額と他部門の金額は、換算してからでないと足せない・割れない。** 換算せずに足すと150倍ずれる。ROI の分母に使うと150倍良く見える。
- 換算が必要な集計は `xdept_mart.mart_brand_investment_return` を使う。この表は換算レートを `marketing_spend_fx_rate` 列に、根拠を `fx_basis` 列に**明示して持っている**。
- デモ環境の換算レートは **1USD = 150.0 JPY 固定**（実務では期中平均レートを使う）。
- **`currency_code` が空の行がある。** 媒体費の明細で通貨が落ちることがある（2026年で約126行）。空の行を JPY と思って集計すると静かに間違う。`marketing_mart.mart_media_efficiency.missing_currency_rows` 列でその場で件数が分かる。

**Related assets**: `rongzi_catalog_dev.xdept_mart.mart_brand_investment_return`, `rongzi_catalog_dev.marketing_mart.mart_media_efficiency`, `rongzi_catalog_dev.xdept_mart.mart_spend_definitions`
**Sources**: `rongzi_catalog_dev.marketing_core.campaign`, `rongzi_catalog_dev.marketing_core.media_spend`, `rongzi_catalog_dev.trade_core.promotion_line`

---

## 17. 投資対効果 / ROI（Brickshouse 全社定義）

**同義語**: ROI, 投資対効果, 投資効率, 費用対効果, リターン, 回収率, 投下効率, return on investment, ROAS, ROMI

**Definition**
Brickshouse には ROI と呼ばれる数字が**3つ**あり、分母も分子も違う。問いの単位で選ぶ。

| 問いの単位 | 使う指標 | 分子 | 分母 |
|---|---|---|---|
| **ブランド** | `xdept_mart.mart_brand_investment_return.return_on_investment` | 店頭実売（JPY・パネル投影） | マーケ投下(USD×150) ＋ 販促費(JPY) |
| **販促イベント** | `trade_mart.mart_promotion_roi.roi` | 販促システム側の自己申告売上 | 販促費（JPY） |
| **媒体** | `marketing_mart.marketing_media_spend.avg_roi_index` | （Nielsen の指数。金額ではない） | — |

**Business use**
- 「マーケの ROI は？」と聞かれたら**ブランド単位**（1行目）で答える。
- `avg_roi_index` は**指数**であって投資回収率ではない。1.2 は「120%回収した」ではなく「基準比1.2」。
- ブランド ROI の分子に**財務の純売上は使えない**。ECM の受注がヘッダ粒度で `sku_id` を持たないため、純売上をブランドに割れない。したがってブランド ROI は**全社 P/L の粗利とは一致しない**。使い方は**ブランド間の相対比較**まで。
- 分母には必ず**換算済みの金額**を使う（→ Page「通貨」）。

**Related assets**: `rongzi_catalog_dev.xdept_mart.mart_brand_investment_return`, `rongzi_catalog_dev.trade_mart.mart_promotion_roi`, `rongzi_catalog_dev.marketing_mart.mart_media_efficiency`
**Sources**: `rongzi_catalog_dev.marketing_core.campaign`, `rongzi_catalog_dev.trade_core.promotion_line`, `rongzi_catalog_dev.sales_core.pos_transaction`

---

## 18. 市場規模・市場シェア（Brickshouse マーケ）

**同義語**: 市場規模, 市場全体, カテゴリ規模, 市場売上, 市場シェア, シェア, 金額シェア, 数量シェア, market size, market share, dollar share, Nielsen, シンジケートデータ, SRI

**Definition**
市場規模の正本は **`marketing_mart.mart_brand_market_position.market_dollar_sales_usd`**（出所 `marketing_core.syndicated_market_data`、`market_type = 'category_total'`、**USD建て**）。2026年の合計は約 **$7.67B（約11,507億円）**。
自社シェアは同じ表の `own_dollar_share_pct`（平均約 **11%**）。

**Business use**
**`syndicated_market_data.dollar_sales` は当社の売上ではない。** 競合他社を含む市場全体の売上である。

| 列 | 意味 | 単位 | 2026年 |
|---|---|---|---|
| `syndicated_market_data.dollar_sales` | **市場全体**（競合込み） | **USD** | $7.67B ≒ 11,507億円 |
| `pos_transaction.dollar_sales` | **自社の店頭実売**（Nielsenパネル約15%ACV投影） | **JPY** | 33.1億円 |

**なぜ紛らわしいか**: この2つは**列名が `dollar_sales` で完全に同じ**。universe（市場全体 / 自社）も単位（USD / JPY）も違うのに、名前では区別できない。混ぜると自社が市場規模に見える（約348倍）。
自社の市場売上が欲しい場合は `market_dollar_sales_usd × own_dollar_share_pct ÷ 100`（同表の `own_market_sales_usd` 列）を使う。これは POS とは出所も通貨も違う別の数字である。

**Related assets**: `rongzi_catalog_dev.marketing_mart.mart_brand_market_position`
**Sources**: `rongzi_catalog_dev.marketing_core.syndicated_market_data`, `rongzi_catalog_dev.sales_core.pos_transaction`

---

## 19. ブランド（Brickshouse 全社定義）

**同義語**: ブランド, 銘柄, 商標, brand, マスターブランド, サブブランド, ブランド名

**Definition**
ブランドマスタの正本は **`rongzi_catalog_dev.marketing_core.brand`**（12ブランド／`brand_id` が hub キー）。
ビール類4・清涼飲料5・健康食品3。`lifecycle_status` が `active` なものが11。

**Business use**
ブランドは**部門をまたぐ hub キー**で、以下がすべて `brand_id` でここを参照している。

| 参照元 | 意味 |
|---|---|
| `master_core.sku.brand_id` | SKU がどのブランドか（商品軸の分析の起点） |
| `sales_core.distribution_point.brand_id` | 配下店舗のブランド別配荷 |
| `trade_core.promotion_line.brand_id` | 販促明細のブランド |
| `trade_core.fund.brand_id` | 販促原資のブランド |
| `marketing_core.campaign` / `media_spend` / `consumer_insight` / `syndicated_market_data` | マーケ側すべて |

ブランド軸で部門を横断する分析は `xdept_mart.mart_brand_investment_return` に集約してある。
`brand.annual_marketing_budget` は **USD建ての予算**で実績ではない（実績は Page「マーケ投下額」）。

**Related assets**: `rongzi_catalog_dev.xdept_mart.mart_brand_investment_return`, `rongzi_catalog_dev.marketing_mart.mart_brand_market_position`
**Sources**: `rongzi_catalog_dev.marketing_core.brand`, `rongzi_catalog_dev.master_core.sku`

---

## 20. キャンペーン（Brickshouse マーケ）

**同義語**: キャンペーン, 施策, 広告キャンペーン, campaign, 投下施策, 媒体施策, プロモーション施策

**Definition**
キャンペーンの正本は **`marketing_core.campaign`**（2026年240件）。`campaign_id` が hub キー。
消化率は `marketing_mart.mart_campaign_performance.burn_rate`（= `actual_spend_usd ÷ planned_budget_usd`）。

**Business use**
- **キャンペーン（マーケ）と販促イベント（営業）は別物。** 販促イベントは `trade_core.promotion_event`（得意先ごとの値引き・什器）、キャンペーンは `marketing_core.campaign`（媒体投下）。ただし `promotion_event.campaign_id` でひも付いており、同じキャンペーンの下で両方が動くことがある。
- `sales_core.order.campaign_id` があるので、受注をキャンペーン軸で見ることはできる。ただし**受注のキャンペーン紐付けは営業入力**であり、投下の効果測定として使うには弱い。
- 投下額の明細は `media_spend`（媒体の購入）と `campaign_execution`（配信の執行）の2系統。**両方を足すと二重計上になる。**

**Related assets**: `rongzi_catalog_dev.marketing_mart.mart_campaign_performance`, `rongzi_catalog_dev.marketing_mart.mart_media_efficiency`
**Sources**: `rongzi_catalog_dev.marketing_core.campaign`, `rongzi_catalog_dev.marketing_core.campaign_execution`, `rongzi_catalog_dev.marketing_core.media_spend`

---

## 21. 消費者調査費（Brickshouse マーケ）

**同義語**: 調査費, 消費者調査, リサーチ費用, 調査プロジェクト, consumer insight, market research, ブランドヘルス, コンセプトテスト, 官能評価, NPS調査

**Definition**
正本は **`marketing_core.consumer_insight.actual_spend_usd`**（**USD建て**）。2026年約 **$2.9M（約4.4億円）**。600プロジェクト。

**Business use**
**これはマーケ投下額ではない。** 媒体やキャンペーンに出したお金ではなく、調査会社に払った調査費である。マーケ投下額の約5%。

ECM の metric view `marketing_consumer_insight` はこの列に **`total_actual_spend_usd` という `marketing_campaign_performance` と完全に同じ名前の measure** を置いている。
「マーケ投下額」を聞かれてこちらを選ぶと、約18分の1の答えになる。

調査の**中身**（NPS・コンセプトテストスコア・官能評価）はこの表の正しい使い道で、`avg_nps_score` / `avg_concept_test_score` / `avg_sensory_score` を使う。

**Related assets**: `rongzi_catalog_dev.marketing_mart.marketing_consumer_insight`, `rongzi_catalog_dev.xdept_mart.mart_spend_definitions`
**Sources**: `rongzi_catalog_dev.marketing_core.consumer_insight`

---

## 22. 媒体費（Brickshouse マーケ）

**同義語**: 媒体費, 媒体投下, メディア費, 広告枠, media spend, 媒体購入, ワーキングメディア, CPM, CPC

**Definition**
正本は **`marketing_mart.marketing_media_spend.total_actual_spend_amount`**（出所 `marketing_core.media_spend`、**USD建て**）。2026年約 **$37.5M（約56.2億円）**。マーケ投下額の約70%。

**Business use**
- 媒体費は**マーケ投下額の一部**。「マーケにいくら使ったか」の答えには使わない（→ Page「マーケ投下額」）。
- チャネル別の効率は `marketing_mart.mart_media_efficiency`（CPM・CPC・CTR・消化率）。
- `working_media_flag = true` が実際に枠に出た分。`false` は制作費・代理店フィー等。**「ワーキングメディア比率」を聞かれたらこのフラグで割る。**
- `roi_index` は Nielsen の**指数**で投資回収率ではない（→ Page「投資対効果 / ROI」）。
- **`currency_code` が空の明細がある。** 集計前に `mart_media_efficiency.missing_currency_rows` を見る（→ Page「通貨」）。

**Related assets**: `rongzi_catalog_dev.marketing_mart.mart_media_efficiency`, `rongzi_catalog_dev.marketing_mart.marketing_media_spend`
**Sources**: `rongzi_catalog_dev.marketing_core.media_spend`
