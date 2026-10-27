# Brickshouse Food and Beverage — 業務用語集（Page の原稿）

置き場所は UC ドメイン **`Brickshouse Food and Beverage`** とそのサブドメイン3本。
**4本とも作成済みで draft ではない**（2026-10-27 に作り直した）。

| タイトルの末尾 | 置くドメイン |
|---|---|
| `（Brickshouse 営業）` `（Brickshouse 販促）` | `Brickshouse Food and Beverage/営業` |
| `（Brickshouse 財務）` | `Brickshouse Food and Beverage/財務` |
| `（Brickshouse マーケ）` | `Brickshouse Food and Beverage/マーケティング` |
| `（Brickshouse 全社定義）` `（Brickshouse 調達）` | `Brickshouse Food and Beverage`（親） |

部門はドメインだけでなく**タイトルと同義語でも識別**する。部門名が固有名詞として効き、
同業55件の他社ドメインの Page に勝ちやすい。

`Related assets` と `Sources` のテーブル名は `rongzi_catalog_dev` から始まる3段で書いてある。
Page の `Sources` 欄は URL しか受け付けないので、**欄は空にして本文末尾の「## Sources」見出しに**書く。

書き方の規約
- 全社語（部門間で衝突する語）: `<語>（Brickshouse 全社定義）` / 同義語に**各部門の呼び方を全部**入れる
- 部門語: `<語>（Brickshouse <部門>）` / 同義語にその部門の言い回し

**鉄則0: 金額を固定で書かない**

絶対額を書くと、パイプラインを回してデータが変わるたびに Genie が
「用語集では1,274.7億円ですが、集計では1,286.1億円でした」と**食い違いを報告する**（実際に起きた）。
用語集の仕事は「**どの列が正本か**」を決めることで、「いくらか」を答えることではない。
金額は Genie が毎回集計すればよい。

比率も同じで、程度が小さいだけである（「投下額の約5%」もデータを測った値）。
**定義から導けることだけを書く。**

| 書く | 書かない |
|---|---|
| 受注は純売上より**大きい**（一部出荷・値引・控除の前だから） | 受注は純売上より22%大きい |
| 原価率 = 発注 ÷ 純売上 | 原価率は約47% |
| 調査費は投下額に**含まれない別物** | 調査費は投下額の約5% |

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

**説明**
税抜き・返品控除後の販売計上額。全社レポーティングで「売上」と言えばこの数字。

**Definition**
純売上 = 請求総額 − 販促値引 − 控除。
`finance_mart.finance_ar_invoice` の `MEASURE(total_net_amount)` が正本。

**Business use**
- 「会社の売上」を聞かれたら必ずこの数字を使う。
- 部門が「売上」と呼ぶ数字が他に4つある。受注（営業の着地見込み・出荷前なので大きい）、発注（調達の支出）、販促精算（得意先への支払い）、店頭実売（Nielsen パネルの投影値）。**どれも純売上ではない。**
- 5つを並べて比べるときは `xdept_mart.mart_revenue_definitions`（月次で1行に揃っている）。
- 出所は `finance_core.ar_invoice`。`invoice_status` で絞らない限り全請求を含む。
- 業界標準データモデル(ECM)の metric view は、上の5つすべてに `total_net_amount` という**同名の measure** を持つ。名前だけでは区別できない。

**Examples**
- 「2026年の売上はいくらですか？」
- 「営業が言う売上と財務が言う売上はなぜ違うのですか？」

**Related assets**: `rongzi_catalog_dev.finance_mart.finance_ar_invoice`, `rongzi_catalog_dev.finance_mart.mart_revenue_reconciliation`, `rongzi_catalog_dev.xdept_mart.mart_revenue_definitions`
**Sources**: `rongzi_catalog_dev.finance_core.ar_invoice`

---

## 2. 原価（Brickshouse 全社定義）

**同義語**: 原価, 標準原価, 単位原価, standard cost, unit cost, 製造原価, 売上原価, 原価率

**説明**
製品1単位を作るのにかかる標準原価。実際原価ではない。

**Definition**
標準原価の正本は `master_mart.product_standard_cost` の `MEASURE(avg_total_standard_cost_per_unit)`。
原価率 = 発注 ÷ 純売上。

**Business use**
- 原価率を聞かれたら `procure_mart.procurement_purchase_order` の `MEASURE(total_net_amount)` ÷ 純売上。**受注を分子にしてはならない**（`sales_mart.sales_order.total_net_amount` と1語違いで、取り違えると100%を超える）。
- `finance_core.finance_standard_cost` と `master_core.product_standard_cost` の2つに原価がある。食い違いの確認は `finance_mart.mart_standard_cost_compare` の `unit_cost_gap_ratio`。
- 単位原価（per_unit）とケース原価（per_case）は別物。どちらを聞かれているか曖昧なら確認する。

**Examples**
- 「2026年の原価率は何パーセントですか？」
- 「製品原価と財務原価が食い違っているSKUはありますか？」

**Related assets**: `rongzi_catalog_dev.finance_mart.mart_standard_cost_compare`, `rongzi_catalog_dev.master_mart.product_standard_cost`
**Sources**: `rongzi_catalog_dev.finance_core.finance_standard_cost`, `rongzi_catalog_dev.master_core.product_standard_cost`

---

## 3. 得意先（Brickshouse 全社定義）

**同義語**: 得意先, 顧客, 取引先, アカウント, account, customer, 販売先, チェーン, 小売

**説明**
商品を売る相手。小売チェーン・卸・EC を含む。

**Definition**
得意先マスタの正本は `sales_core.account`。`account_id` が営業・財務・販促を貫く hub キー。

**Business use**
- 得意先を軸に部門を横断して見るときは `xdept_mart.mart_customer_360`（受注・純売上・未回収・販促費・精算・控除・店頭実売が1行に揃っている）。
- 得意先名は「<社名> <地域>支社」の形。**社名だけでは一意にならない**ので、部分一致で聞かれたら該当する支社を全部示す。
- チャネル区分は `channel`、地域は `shipping_state`。

**Examples**
- 「フレッシュストア 関東支社の受注推移を見せてください」
- 「純売上の上位10得意先を教えてください」

**Related assets**: `rongzi_catalog_dev.xdept_mart.mart_customer_360`, `rongzi_catalog_dev.sales_mart.customer_account_overview`
**Sources**: `rongzi_catalog_dev.sales_core.account`

---

## 4. 商品（Brickshouse 全社定義）

**同義語**: 商品, 製品, SKU, 品目, product, item, 品番, 商品コード

**説明**
販売する製品の単位。SKU 粒度で管理する。

**Definition**
商品マスタの正本は `master_core.sku`。`sku_id` が hub キー。

**Business use**
- `product_line` が事業区分（ビール類 / 清涼飲料 / 健康食品）、`flavor_variety` が銘柄。
- **`sales_core.order` は受注ヘッダ粒度で `sku_id` を持たない。** 商品軸の分析は `pos_transaction`（店頭実売）・`distribution_point`（配下）・`promotion_line`（販促明細）で行う。
- ブランドとの関係は `sku.brand_id` で `marketing_core.brand` を参照する。

**Examples**
- 「商品別の店頭実売の上位を教えてください」
- 「ビール類の配下率が低いSKUはどれですか？」

**Related assets**: `rongzi_catalog_dev.master_core.sku`, `rongzi_catalog_dev.master_core.category`
**Sources**: `rongzi_catalog_dev.master_core.sku`

---

## 5. 受注（Brickshouse 営業）

**同義語**: 受注, 受注高, 受注金額, オーダー, order, 受注残, 営業の売上, 着地見込み

**説明**
得意先から受けた注文の金額。出荷・請求の前の段階。

**Definition**
`sales_mart.sales_order` の `MEASURE(total_net_amount)`。

**Business use**
- 営業の着地見込みに使う。**「会社の売上」として使ってはならない**（売上は純売上 → 売上の Page）。
- 一部出荷・値引・控除の前の金額なので、**純売上より大きくなる。**
- `order_status` で未出荷・キャンセルを含むかが変わる。全社の数字と比べるときは状態を明示する。
- 受注ヘッダ粒度なので `sku_id` を持たない。商品軸では使えない。

**Examples**
- 「今期の受注の着地見込みはいくらですか？」
- 「受注と純売上の差が大きい得意先はどこですか？」

**Related assets**: `rongzi_catalog_dev.sales_mart.mart_sales_performance`, `rongzi_catalog_dev.xdept_mart.mart_revenue_definitions`
**Sources**: `rongzi_catalog_dev.sales_core.order`

---

## 6. 配下率（Brickshouse 営業）

**同義語**: 配下率, 配荷率, ACV, ACV加重配下, TDP, numeric distribution, 取扱率, 棚取り

**説明**
自社商品が置かれている店舗の広がり。棚取りの進捗を見る。

**Definition**
`sales_core.distribution_point.acv_weighted_distribution_pct`（ACV加重配下率）。

**Business use**
- Nielsen 由来の指標。店舗数の単純比率ではなく、店舗の売上規模で重みづけした値。
- ブランド軸・SKU軸で見る。`brand_id` / `sku_id` を持つ。
- 配下率が低いのに販促費を投じている組み合わせは、棚が取れていないのに売り場投資をしている状態。

**Examples**
- 「配下率が低いブランドはどれですか？」
- 「配下率と販促費の関係を見せてください」

**Related assets**: `rongzi_catalog_dev.sales_mart.mart_account_coverage`
**Sources**: `rongzi_catalog_dev.sales_core.distribution_point`

---

## 7. 店頭実売（Brickshouse 営業）

**同義語**: 店頭実売, 店頭消化, sell-out, POS, スキャンデータ, 実売, 消化

**説明**
店頭で消費者に売れた金額（sell-out）。自社の出荷額ではない。

**Definition**
`sales_core.pos_transaction.dollar_sales`。**JPY建て。**

**Business use**
- 出所は Nielsen の syndicated パネルで、全店 census ではなく**約15% ACV の投影値**。
- **当社の売上（sell-in）と絶対額で比較してはならない。** 母数が違う。比較は**伸び率・指数**で行う。
- sell-in と sell-out の乖離（棚の消化不足・過剰出荷）を見る目的に使う。
- `marketing_core.syndicated_market_data.dollar_sales` と**列名が完全に同じ**だが別物（あちらは市場全体・USD建て）。

**Examples**
- 「当社の店頭での売れ行きを前年比で見せてください」
- 「出荷と店頭実売の伸び率が乖離しているブランドはありますか？」

**Related assets**: `rongzi_catalog_dev.sales_mart.mart_sales_performance`
**Sources**: `rongzi_catalog_dev.sales_core.pos_transaction`

---

## 8. 売上計上のタイミング（Brickshouse 財務）

**同義語**: 売上計上, 計上タイミング, 収益認識, revenue recognition, 計上月, 計上日, 期ズレ, カットオフ

**説明**
いつ売上として計上されるか、という時点の決まり。

**Definition**
売上計上は請求日（`finance_core.ar_invoice.invoice_date`）基準。受注日・出荷日ではない。

**Business use**
- 月次の売上を聞かれたら請求日で月を切る。受注日で切ると営業の数字になり、財務の月次と合わない。
- 段ごとの照合（請求総額 → 値引・控除 → 純売上 → 入金）は `finance_mart.mart_revenue_reconciliation`。**この表の粒度は 月 × 得意先 × 請求ステータス**なので、全社の月次を聞かれたら得意先と状態を合計して月だけで集計する。
- 入金（`payment_amount`）と残高（`open_receivable_amount`）はこの表にしかない。

**Examples**
- 「月次の純売上と入金の推移を並べてください」
- 「受注した月と売上になった月がずれているのはなぜですか？」

**Related assets**: `rongzi_catalog_dev.finance_mart.mart_revenue_reconciliation`, `rongzi_catalog_dev.xdept_mart.mart_revenue_definitions`
**Sources**: `rongzi_catalog_dev.finance_core.ar_invoice`

---

## 9. レベニューリーケージ（Brickshouse 財務）

**同義語**: レベニューリーケージ, 売上の漏れ, revenue leakage, 値引・控除, 販促による目減り

**説明**
請求したのに売上として残らなかった金額。

**Definition**
レベニューリーケージ = `finance_core.ar_invoice` の `trade_discount_amount` + `deduction_amount`。

**Business use**
- **未回収売掛（`open_amount`）とは別物。** 未回収はまだ入っていないお金、リーケージは初めから失われたお金。
- 値引（trade_discount）は販促の取り決めによるもの、控除（deduction）は得意先が支払時に差し引いたもの。原因が違うので分けて見る。
- 控除の理由別の内訳は `trade_core.deduction.deduction_type`。

**Examples**
- 「レベニューリーケージはいくらですか？」
- 「値引と控除のどちらが大きいですか？」

**Related assets**: `rongzi_catalog_dev.xdept_mart.mart_customer_360`, `rongzi_catalog_dev.trade_mart.mart_trade_spend_flow`
**Sources**: `rongzi_catalog_dev.finance_core.ar_invoice`, `rongzi_catalog_dev.trade_core.deduction`

---

## 10. 販促費（Brickshouse 販促）

**同義語**: 販促費, 販促, トレードスペンド, trade spend, プロモーション費, 販促投資

**説明**
得意先との売り場づくりに投じるお金。値引・什器・チラシなど。

**Definition**
`trade_core.promotion_event.promotional_spend_net`。横断で比べるときは `xdept_mart.mart_spend_definitions`。

**Business use**
- **`actual_revenue` は販促イベントの自己申告値であり、会社の売上ではない。** 売上と並べてはならない。
- 販促費（投じる計画・実績）と販促精算（実際に支払った額）と控除（得意先が差し引いた額）は**3つとも別物**。足すと二重計上になる。
- マーケ投下額（USD建て）とは通貨が違う。合算するなら換算が必要（→ 通貨の Page）。

**Examples**
- 「販促費が純売上に占める比率が高い得意先を教えてください」
- 「来月開始予定の販促イベントは何件ありますか？」

**Related assets**: `rongzi_catalog_dev.trade_mart.mart_promotion_roi`, `rongzi_catalog_dev.trade_mart.mart_trade_spend_flow`
**Sources**: `rongzi_catalog_dev.trade_core.promotion_event`

---

## 11. 販促精算（Brickshouse 販促）

**同義語**: 販促精算, 精算, settlement, クレーム精算, 販促支払, リベート精算

**説明**
得意先の請求（claim）に対して当社が実際に支払った額。

**Definition**
`trade_mart.trade_settlement` の `MEASURE(total_net_amount)`。
`net_amount = original_claim_amount + adjustment_amount`。

**Business use**
- **売上ではない。** 売上に足すと二重計上になる（売上側では `ar_invoice.deduction_amount` としてマイナスに反映されている）。
- 引当（`trade_core.accrual`）との差が未精算の残り。精算率を聞かれたら精算額 ÷ 引当額。
- `settlement_status` で未処理・処理済みが分かれる。

**Examples**
- 「引当した販促費のうち実際に精算されたのは何パーセントですか？」
- 「販促精算額はいくらですか？」

**Related assets**: `rongzi_catalog_dev.trade_mart.trade_settlement`, `rongzi_catalog_dev.trade_mart.mart_trade_spend_flow`
**Sources**: `rongzi_catalog_dev.trade_core.settlement`

---

## 12. 控除（Brickshouse 販促）

**同義語**: 控除, ディダクション, deduction, チャージバック, 差し引き, 減額

**説明**
得意先が支払時に差し引いた金額。純売上を押し下げる。

**Definition**
`trade_core.deduction.net_amount`。

**Business use**
- `deduction_type` は promotion / shortage / damage / pricing / return。理由別に見ると原因部署が分かる。
- 売上側では `ar_invoice.deduction_amount` に反映され、純売上を押し下げている。**控除を売上に足してはならない。**
- 係争中かどうかは `deduction_status = 'disputed'`（`dispute_flag` も同じ行で true。どちらで数えても同じ）。

**Examples**
- 「係争中の控除はいくらありますか？」
- 「控除の理由別の内訳を教えてください」

**Related assets**: `rongzi_catalog_dev.trade_mart.mart_trade_spend_flow`, `rongzi_catalog_dev.finance_mart.finance_ar_invoice`
**Sources**: `rongzi_catalog_dev.trade_core.deduction`

---

## 13. 発注（Brickshouse 調達）

**同義語**: 発注, 購買, 仕入, purchase order, PO, 調達金額

**説明**
当社が仕入・調達のために支払う発注額。

**Definition**
`procure_mart.procurement_purchase_order` の `MEASURE(total_net_amount)`。

**Business use**
- **売上ではない。** `total_net_amount` という売上と同名の measure を持つが、当社が払う金額。
- 原価率の算出（発注 ÷ 純売上）の**分子**に使う。受注（`sales_mart.sales_order.total_net_amount`）を分子にすると100%を超える。
- 買掛（`finance_mart.finance_ap_invoice`）も同様に売上ではない。発注が注文時点、買掛が請求時点。
- 三者照合が合っていない買掛請求は `finance_core.ap_invoice.match_status <> 'matched'`。

**Examples**
- 「2026年の原価率を教えてください」
- 「三者照合が合っていない買掛請求はどれですか？」

**Related assets**: `rongzi_catalog_dev.procure_mart.procurement_purchase_order`, `rongzi_catalog_dev.finance_mart.finance_ap_invoice`
**Sources**: `rongzi_catalog_dev.procure_core.purchase_order`, `rongzi_catalog_dev.finance_core.ap_invoice`

---

## 14. チャネル（Brickshouse 全社定義）

**同義語**: チャネル, 業態, channel, 販路, 取引形態

**説明**
得意先の業態区分。構成比を見る標準軸。

**Definition**
`sales_core.account.channel`。区分は SM / CVS / DgS / 卸 / EC の5つ。

**Business use**
- 受注・純売上・販促費の構成比を見るときの標準軸。
- `order.channel` と `pos_transaction.store_format` も同じ区分を使う。
- 業界標準データモデル(ECM)の辞書には `retail` / `foodservice` などの英語値が書かれているが、**当社のデータは上の5区分**。辞書の値で絞ると0件になる。

**Examples**
- 「チャネル別の純売上構成を教えてください」
- 「CVSの販促費比率は他チャネルと比べてどうですか？」

**Related assets**: `rongzi_catalog_dev.sales_mart.customer_account_overview`, `rongzi_catalog_dev.xdept_mart.mart_customer_360`
**Sources**: `rongzi_catalog_dev.sales_core.account`

---

## 15. マーケ投下額（Brickshouse マーケ）

**同義語**: マーケ投下額, マーケティング投下額, マーケ費, マーケティング費用, 広宣費, 広告宣伝費, 投下額, marketing spend, media investment, A&P, ATL費用, キャンペーン費用

**説明**
マーケティングがキャンペーンに投じたお金。

**Definition**
`marketing_mart.marketing_campaign_performance` の `MEASURE(total_actual_spend_usd)`。**USD建て。**

**Business use**
- **単位は USD。** 他部門（営業・財務・販促）は JPY 建てなので、足すには換算が必要（→ 通貨の Page）。
- 内訳は媒体費＋制作費・代理店フィー等。**媒体費だけでは投下額にならない。**
- 同名で紛らわしいものが3つある。消費者調査費（`marketing_consumer_insight.total_actual_spend_usd`）は調査会社に払う費用で投下額ではない。媒体費（`marketing_media_spend.total_actual_spend_amount`）は投下額の一部。`brand.annual_marketing_budget` は予算であって実績ではない。
- 販促費（営業・JPY）とは別物。両方を合わせた総投資額が必要なら `xdept_mart.mart_spend_definitions`。

**Examples**
- 「2026年のマーケティング投下額はいくらですか？」
- 「マーケ投下額と販促費を足した総投資額はいくらですか？」

**Related assets**: `rongzi_catalog_dev.marketing_mart.marketing_campaign_performance`, `rongzi_catalog_dev.marketing_mart.mart_campaign_performance`, `rongzi_catalog_dev.xdept_mart.mart_spend_definitions`
**Sources**: `rongzi_catalog_dev.marketing_core.campaign`

---

## 16. 通貨（Brickshouse 全社定義）

**同義語**: 通貨, 建値, 為替, currency, USD, ドル建て, 円建て, JPY, 換算, 為替レート, FX

**説明**
金額がどの通貨で記録されているか、という部門ごとの決まり。

**Definition**
営業・財務・販促（`sales_*` / `finance_*` / `trade_*`）は **JPY**。マーケ（`marketing_*`）は **USD**。

**Business use**
- **マーケの金額と他部門の金額は、換算してからでないと足せない・割れない。** 換算せずに足すと150倍ずれ、ROI の分母に使うと150倍良く見える。
- 換算が必要な集計は `xdept_mart.mart_brand_investment_return`。換算レートを `marketing_spend_fx_rate` 列、根拠を `fx_basis` 列に明示して持っている。
- デモ環境の換算レートは 1USD = 150.0 JPY 固定（実務では期中平均レートを使う）。
- **`currency_code` が空の行がある**（媒体費の明細）。空を JPY と見なしてはならない。件数は `marketing_mart.mart_media_efficiency.missing_currency_rows` で分かる。
- 市場データ（`syndicated_market_data`）も USD。Nielsen の元データが USD のため。

**Examples**
- 「マーケ投下額と販促費を合わせるといくらですか？」
- 「通貨が入っていない媒体費の明細はありますか？」

**Related assets**: `rongzi_catalog_dev.xdept_mart.mart_brand_investment_return`, `rongzi_catalog_dev.marketing_mart.mart_media_efficiency`, `rongzi_catalog_dev.xdept_mart.mart_spend_definitions`
**Sources**: `rongzi_catalog_dev.marketing_core.campaign`, `rongzi_catalog_dev.marketing_core.media_spend`, `rongzi_catalog_dev.trade_core.promotion_line`

---

## 17. 投資対効果 / ROI（Brickshouse 全社定義）

**同義語**: ROI, 投資対効果, 投資効率, 費用対効果, リターン, 回収率, 投下効率, return on investment, ROAS, ROMI

**説明**
投じたお金がどれだけ returns を生んだか。3種類あり、混同しやすい。

**Definition**
ブランド単位の ROI は `xdept_mart.mart_brand_investment_return.return_on_investment`。これが「マーケのROI」。

**Business use**
- 販促イベント単位の ROI は `trade_mart.mart_promotion_roi.roi`。対象が違うので比較できない。
- `marketing_mart.marketing_media_spend` の `MEASURE(avg_roi_index)` は**指数**であって投資回収率ではない。1.2 は「120%回収した」ではなく「基準比1.2」。
- ブランド ROI は分子が市場規模 × シェア、分母が換算後のマーケ投下額＋販促費。**分母の通貨を揃えないと150倍良く見える。**
- どの ROI を聞かれているか曖昧なら、対象（ブランド / 販促イベント / 媒体）を確認する。

**Examples**
- 「ブランド別の投資対効果の上位を教えてください」
- 「販促イベントのROIとマーケのROIは同じものですか？」

**Related assets**: `rongzi_catalog_dev.xdept_mart.mart_brand_investment_return`, `rongzi_catalog_dev.trade_mart.mart_promotion_roi`, `rongzi_catalog_dev.marketing_mart.mart_media_efficiency`
**Sources**: `rongzi_catalog_dev.marketing_core.campaign`, `rongzi_catalog_dev.trade_core.promotion_line`, `rongzi_catalog_dev.sales_core.pos_transaction`

---

## 18. 市場規模・市場シェア（Brickshouse マーケ）

**同義語**: 市場規模, 市場全体, カテゴリ規模, 市場売上, 市場シェア, シェア, 金額シェア, 数量シェア, market size, market share, dollar share, Nielsen, シンジケートデータ, SRI

**説明**
自社と競合を合わせた市場全体の規模と、その中での自社の取り分。

**Definition**
市場規模は `marketing_mart.mart_brand_market_position.market_dollar_sales_usd`（`market_type = 'category_total'`、**USD建て**）。自社シェアは同じ表の `own_dollar_share_pct`。

**Business use**
- 出所は `marketing_core.syndicated_market_data`。**競合を含む市場全体**なので、自社の売上より大きい。
- `syndicated_market_data.dollar_sales` と `sales_core.pos_transaction.dollar_sales` は**列名が完全に同じだが別物**。前者は市場全体・USD、後者は自社の店頭実売・JPY・パネル投影値。混ぜると自社が市場規模に見える。
- 自社の市場売上が必要なら `market_dollar_sales_usd × dollar_share_pct ÷ 100`。
- 市場は地域別に分かれている。全国の数字が必要なら地域を合計する（全国という行は持たない）。

**Examples**
- 「ブランド別の市場シェアを教えてください」
- 「市場規模と当社の店頭実売はどう違うのですか？」

**Related assets**: `rongzi_catalog_dev.marketing_mart.mart_brand_market_position`
**Sources**: `rongzi_catalog_dev.marketing_core.syndicated_market_data`, `rongzi_catalog_dev.sales_core.pos_transaction`

---

## 19. ブランド（Brickshouse 全社定義）

**同義語**: ブランド, 銘柄, 商標, brand, マスターブランド, サブブランド, ブランド名

**説明**
商品をまとめる銘柄の単位。部門をまたぐ軸になる。

**Definition**
ブランドマスタの正本は `marketing_core.brand`。`brand_id` が hub キー。

**Business use**
- ビール類・清涼飲料・健康食品の3事業にまたがる。`lifecycle_status` が `active` なものが現行ブランド。
- `sku.brand_id` / `distribution_point.brand_id` / `promotion_line.brand_id` / `fund.brand_id` がすべてここを参照する。**ブランド軸で部門を横断できる唯一のキー。**
- ブランド単位の投資対効果は `xdept_mart.mart_brand_investment_return`（マーケ USD と販促 JPY を換算して揃えてある）。
- `annual_marketing_budget` は**予算**であって実績ではない。実績は `marketing_campaign_performance`。

**Examples**
- 「ブランド別の投資対効果を教えてください」
- 「認知率が低いブランドはどれですか？」

**Related assets**: `rongzi_catalog_dev.xdept_mart.mart_brand_investment_return`, `rongzi_catalog_dev.marketing_mart.mart_brand_market_position`
**Sources**: `rongzi_catalog_dev.marketing_core.brand`, `rongzi_catalog_dev.master_core.sku`

---

## 20. キャンペーン（Brickshouse マーケ）

**同義語**: キャンペーン, 施策, 広告キャンペーン, campaign, 投下施策, 媒体施策, プロモーション施策

**説明**
媒体に投下するマーケティングの施策単位。

**Definition**
キャンペーンの正本は `marketing_core.campaign`。`campaign_id` が hub キー。消化率は `marketing_mart.mart_campaign_performance.burn_rate`。

**Business use**
- **キャンペーン（マーケ）と販促イベント（営業）は別物。** 販促イベントは `trade_core.promotion_event`（得意先ごとの値引き・什器）、キャンペーンは媒体投下。ただし `promotion_event.campaign_id` でひも付いており、同じキャンペーンの下で両方が動くことがある。
- 投下額の明細は `media_spend`（媒体の購入）と `campaign_execution`（配信の執行）の2系統。**両方を足すと二重計上になる。**
- `sales_core.order.campaign_id` で受注をキャンペーン軸で見ることはできるが、紐付けは営業入力なので効果測定には弱い。
- 金額は USD 建て。

**Examples**
- 「予算消化率が低いキャンペーンはどれですか？」
- 「終了したキャンペーンの実績を教えてください」

**Related assets**: `rongzi_catalog_dev.marketing_mart.mart_campaign_performance`, `rongzi_catalog_dev.marketing_mart.mart_media_efficiency`
**Sources**: `rongzi_catalog_dev.marketing_core.campaign`, `rongzi_catalog_dev.marketing_core.campaign_execution`, `rongzi_catalog_dev.marketing_core.media_spend`

---

## 21. 消費者調査費（Brickshouse マーケ）

**同義語**: 調査費, 消費者調査, リサーチ費用, 調査プロジェクト, consumer insight, market research, ブランドヘルス, コンセプトテスト, 官能評価, NPS調査

**説明**
消費者調査に払った費用。調査会社への支払い。

**Definition**
`marketing_mart.marketing_consumer_insight` の `MEASURE(total_actual_spend_usd)`。**USD建て。**

**Business use**
- **これはマーケ投下額ではない。** 媒体やキャンペーンに出したお金ではなく、調査プロジェクトの費用。
- `marketing_campaign_performance.total_actual_spend_usd` と**同名の measure** を持つので取り違えやすい。「投下額」を聞かれてこちらを返してはならない。
- 調査の結果指標は同じ表の `avg_nps_score` / `avg_concept_test_score` / `avg_sensory_score`。
- `insight_category` で調査の種類が分かれる。

**Examples**
- 「消費者調査の費用はマーケティング投下額に含まれますか？」
- 「NPSが低いブランドはどれですか？」

**Related assets**: `rongzi_catalog_dev.marketing_mart.marketing_consumer_insight`, `rongzi_catalog_dev.xdept_mart.mart_spend_definitions`
**Sources**: `rongzi_catalog_dev.marketing_core.consumer_insight`

---

## 22. 媒体費（Brickshouse マーケ）

**同義語**: 媒体費, 媒体投下, メディア費, 広告枠, media spend, 媒体購入, ワーキングメディア, CPM, CPC

**説明**
媒体の購入に払ったお金。マーケ投下額の一部。

**Definition**
`marketing_mart.marketing_media_spend` の `MEASURE(total_actual_spend_amount)`。**USD建て。**

**Business use**
- **マーケ投下額の一部**であり、これだけでは投下額にならない（制作費・代理店フィーを含まない）。
- `media_channel` / `media_type` で媒体別に分かれる。効率指標は同じ表の `MEASURE(cpm)` / `MEASURE(cpc)`。
- `MEASURE(avg_roi_index)` は**指数**で投資回収率ではない（→ 投資対効果 / ROI の Page）。
- **`currency_code` が空の明細がある。** 空を JPY と見なしてはならない（→ 通貨の Page）。

**Examples**
- 「2026年の媒体費が多いチャネルはどれですか？」
- 「媒体の明細で通貨が入っていないものはありますか？」

**Related assets**: `rongzi_catalog_dev.marketing_mart.mart_media_efficiency`, `rongzi_catalog_dev.marketing_mart.marketing_media_spend`
**Sources**: `rongzi_catalog_dev.marketing_core.media_spend`

---
