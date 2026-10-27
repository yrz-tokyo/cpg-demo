# CPG 全社部門デモ ＋ FE Bar 構想メモ

> **これは 2026-10-25 時点の着手前メモで、最終成果と食い違う箇所がある。**
> 確定した仕様・数字は `00_SUBMISSION.md`（結論）と `BUILD_LOG.md`（全工程）が正。
> 特にこのメモの後で変わった点: 部門は9→**4**（営業/財務/マーケ/横断）、
> ドメイン上限で作れなかった subdomain は枠を空けて**営業・財務の2本を作成済み**、
> テーブルは24→**30**（マーケ6本追加）。


作成 2026-10-25 / 前提: データモデル = `databricks-industry-solutions/lakehouse-industry-data-models` の `food_beverage/v1`（実機クローンして実測済み）

---

## 結論（先に）

1. **部署は「全部」で正しい。ただし均等に深掘るのは破綻する。**
   1本の横断シナリオ（新商品の全国上市ゲート）を背骨にし、9部門はそこへの入口として置く。深掘りは3部門ペアだけ、残りは1問ギャラリー。

2. **このデータモデルは「意味論の設計図」として極めて使える。ただしデータは入っていない。**
   DDL・PK/FK・COMMENT・metric view・RDFSオントロジーは完備。一方で中身の行は installer の疎通用サンプル（最大100行/表・時系列なし）だけ。分析に耐えるデータ生成は自分の仕事になる。

3. **最小限（Genie One + Ontology + Dashboard）では FE Bar は通らない。**
   必須6コンポーネントのうち Lakeflow / Lakebase / ML・GenAI / App の**4つが未充足**。つまり「さらに作るか」は選択ではなく要件。逆に言えば、この4つを横断シナリオの中に自然に埋める設計にできれば、そのまま高得点の筋になる。

そしてもう一点、意見として:

4. **「他人が作った Page / metric view が答えを壊す」という懸念を、デモの主題そのものに昇格させるべき。**
   これは回避すべき事故ではなく、全社で Genie One を入れる顧客が必ず踏む構造的な問題。詳細は §4。

---

## 1. どの部署にするか

### 1.1 ECM 19ドメイン → 9部門への割り当て

| 部門 | 使う ECM ドメイン | 代表エンティティ |
|---|---|---|
| 営業 | sales, customer, trade, pricing | order, account, territory, promotion_event, price_list |
| マーケティング | marketing | brand, campaign, media_spend, consumer_insight |
| 研究開発（R&D） | research, product, ingredient | rd_project, formulation, sku, raw_material, spec |
| 生産 | manufacturing, maintenance | plant, line, production_order, oee, asset |
| 品質・薬事 | quality, regulatory | capa, inspection_lot, product_registration, recall_event |
| 調達 | procurement | supplier, purchase_contract, scorecard |
| 物流・SCM | distribution, supply, inventory | center, shipment, otif_record, network_node, stock_position |
| 財務 | finance | cost_center, gl_account, profit_center |
| 人事 | workforce | employee, position, certification, labor_schedule |

19ドメインのうち sustainability だけ余る。ここは無理に部門化せず、財務/生産の脚注（CO2・水使用量）として扱うのが素直。

### 1.2 横断が成立する根拠 — 「鍵」が実在する

ECM の cross-domain FK を実測すると **1,136本**。参照される親テーブル上位がそのまま横断の背骨になる。

| 親テーブル | 被参照数 | 意味 |
|---|---|---|
| `workforce.employee` | 233 | **全18ドメインから参照**。人事が独立部門でなく全社の鍵 |
| `product.sku` | 93 | 商品が営業・生産・品質・R&D・物流を貫く |
| `customer.account` | 69 | 得意先が営業・販促・物流・与信を貫く |
| `procurement.supplier` | 49 | 原料の出自 |
| `finance.cost_center` | 47 | 金額の帰属先 |
| `manufacturing.plant` | 47 | 作る場所 |
| `research.rd_project` | 39 | 開発案件 |
| `regulatory.product_registration` | 38 | 届出・表示 |
| `marketing.brand` | 28 | ブランド |

**ここが重要**: 「人事のデータが全部門から参照される」のは、このモデルが単にドメインを並べたのではなく、人（誰が検査したか・誰が承認したか・誰がラインに立ったか）を横断キーに置いているということ。人事部門をデモに入れる理由が、データ構造から説明できる。横断クエリの説得力はここから出る。

### 1.3 通しシナリオ — 「機能性表示食品の新商品を、既存のビール・飲料チャネルで全国上市する」

CPG で最も部門横断的な業務プロセスは新商品上市（NPD → 上市ゲート）。1つの意思決定に9部門全部が利害を持つので、ペルソナを無理なく全部出せる。キリン型（ビール＋飲料＋健康食品）の設定とも合う。

ゲート会議の問い: **「来月第1週の全国配荷、GO か NO-GO か」**

| 部門 | この問いに対する持ち場 | データの出どころ |
|---|---|---|
| R&D | 処方は固まったか／官能評価は閾値を越えたか | research.rd_project, ingredient.spec |
| 品質・薬事 | 機能性表示の届出は受理されたか／表示は通るか | regulatory.product_registration, quality.inspection_lot |
| 調達 | 原料は初回3ヶ月分確保できたか／MOQとリードタイム | procurement.supplier, ingredient.raw_material |
| 生産 | ラインは空くか／切替で既存SKUを犠牲にしないか | manufacturing.line, production_order, OEE |
| 人事 | そのラインに資格保有者（HACCP/食品衛生）が足りるか | workforce.employee.certification, labor_schedule |
| 物流 | 初回配荷はDCに積めるか／OTIFは守れるか | distribution.center, otif_record, inventory |
| 営業 | 棚は取れたか／初回受注はいくら積んだか | sales.order, customer.account, trade.promotion_event |
| マーケ | 投下計画と認知の仮説 | marketing.campaign, media_spend |
| 財務 | 初年度の粗利と回収／どの原価センターに乗るか | finance.cost_center, gl_account |

**連鎖を1本仕込む**（前ビルドの P0001 と同じ手口）: 原料サプライヤのリードタイム遅延 → 初回生産ロットが2週遅れ → 資格者シフトが先に別ラインへ確定済み → 配荷が1週スリップ → 営業の初回受注が棚替え期を外す → 販促費が先に消える → 財務の初年度粗利が計画未達。
これを1本植えておくと、**どの部門の入口から入っても同じ事実にたどり着く**ことが証明できる。横断の価値はこれでしか示せない。

### 1.4 部長と現場は「質問の形」が違う

ペルソナを2セット作る意味はここにある。ロールで分けるのではなく、**問いの構造**で分ける。

| | 部長（判断する人） | 現場（動かす人） |
|---|---|---|
| 問いの形 | 横断・集約・比較・「なぜ」 | 単票・特定・「次の一手」 |
| 例 | 「上市が1週遅れた場合、初年度粗利の着地はどう変わる？」 | 「来週の第2ラインで資格が切れる人は誰？代替は？」 |
| 時間軸 | 四半期・年度 | 今日・今週 |
| 効く機能 | metric view（定義の一貫性）、Page（用語の統一）、認定 | 外部ツール連携（カレンダー・Drive）、Lakebase 書き戻し |
| 求める出力 | 1枚の着地見通し | アクションと相手の名前 |
| 失敗モード | 定義が部署で違って数字が合わない | 答えが出ても次の行動に繋がらない |

この分け方だと「coworker としての Genie One」が説明しやすい。部長には**同じ言葉で答える同僚**、現場には**手を動かす同僚**。

### 1.5 深掘りとギャラリーの切り分け

| 扱い | 部門 | 理由 |
|---|---|---|
| 深掘り（往復3〜4ターン・書き戻しまで） | 生産＋人事 / 営業＋財務 / 品質・薬事 | 連鎖の起点・金額の着地・CPG固有性がここに集まる |
| 1問ギャラリー（質問→回答→引用元まで） | R&D, 調達, マーケ, 物流 | breadth の証明に足る |

ロールプレイは20〜30分。深掘り3本で15分、ギャラリー4問で5分、残りで価値訴求と質疑。14ペルソナを均等に回すと1人90秒で、何も伝わらない。

---

## 2. データモデルの中身と、使えるか

### 2.1 実測した中身

| | ECM（Expanded Coverage） | MVM（Minimum Viable） |
|---|---|---|
| ドメイン | 19 | 14 |
| テーブル | 376 | 157 |
| 属性 | 13,110 | 6,331 |
| FK | 1,748（うち cross-domain 1,136） | 1,287 |
| metric view | 92 | 123 |
| 人事 / 保全 / 研究 / 価格 / サステナ | **あり** | なし |

同梱物（両方）:
- `schemas/*.sql` — `CREATE OR REPLACE TABLE` 形式の DDL。**テーブルCOMMENT と全カラムCOMMENT が入っている**。しかも列コメントに `Valid values are 'active|inactive|terminated'` のような値域が書かれている。Genie のための記述がすでに存在する、というのがこのモデルの一番の価値。
- `schemas/*_cross_domain_foreign_keys_*.sql` — 横断FKを `ALTER TABLE ... ADD CONSTRAINT` で分離。ここだけ差し替えれば関係性を調整できる構造。
- `metrics/*.sql` — `CREATE OR REPLACE VIEW ... WITH METRICS LANGUAGE YAML`（version 1.1）。dimensions / measures にコメント付き。**そのまま UC metric view になる。**
- `ontology/*.ttl` — RDFS。ECM で 50,261行。ドメイン＝クラス、テーブル＝サブクラス、COMMENT＝rdfs:comment の構造。
- `diagram/*.txt`（DBML）、`docs/*.csv|xlsx`（データディクショナリ）、`model.json`（installer/viewer 入力）

### 2.2 入っていないもの — ここが設計の分かれ目

- **データがない。** installer の `generate_samples` で生成できるが、`SAMPLE_ROW_CHOICES = ["5","10","20","50","100"]`。決定論シード、FK整合は保証、自由記述列だけ LLM で現実味を足す。**疎通確認用であって分析用ではない**。時系列・分布・金額・季節性・仕込んだ異常がない。
- **Bronze も Gold もない。** これは silver 相当の論理モデル。取込も集計マートもない。
- **パイプラインがない。** FE Bar の Lakeflow 要件はまるごと自作。
- **カタログ名がハードコード。** DDL も metric view も `food_beverage_ecm` 前提。置換が必要。

結論: **意味論（COMMENT・FK・metric view・オントロジー）をもらい、データとパイプラインは自分で作る**。これが正しい使い方。逆に、意味論を自分で書こうとすると9部門分の用語定義で数日溶けるので、ここをもらえるのは大きい。

### 2.3 ECM か MVM か → ECM の部分集合

人事・研究・保全・価格が MVM には無い。「全部門」をやるなら ECM 一択。ただし376テーブルは入れない。

**採用方針: ECM から約45テーブルを抜く。** 選定基準は §1.2 の hub 9本を全部含めること。hub が欠けると横断クエリが成立しない。残りは各部門4本前後（マスタ1＋トランザクション2＋計画/実績1）。

### 2.4 FE Bar 上の注意（重要）

- このリポジトリは public な industry-solutions であり **go/solution-builder ではない**ので、使うこと自体は問題ない。ただし FE Bar は「the work, decisions, and narrative are yours」を見る。**376テーブルの生成DDLをそのままコミットして自分の成果物として出すのは筋が悪い。** サブセット選定・改変・日本語化の判断を自分で記録し、ナラティブに「何を借りて、何を自分で決めたか」を明記する。
- **評価スコアラは 30ファイル / 9,000字/ファイル / 合計90,000字しか読まない。** DDL をリポジトリ直下に置くと、この枠をDDLが食い潰してエビデンスが読まれない。これは §3.5 で詳述。

---

## 3. FE Bar を高得点で通すには

### 3.1 必須6コンポーネントの充当（最小限のどこが足りないか）

| # | 必須 | 「最小限」での状態 | 充当案 |
|---|---|---|---|
| 1 | **Lakeflow** | ✗ 未充足 | 合成生ファイルを Volume に着地 → SDP で bronze（`read_files`）→ silver（industry model の45表・expectations・PK/FK宣言）→ gold（部門別マート9本）。**横断の鍵の整合をここで作る**ので、後段の全機能の土台になる |
| 2 | **Unity Catalog** | △ 部分的 | PK/FK・COMMENT（モデル同梱）＋ **Domains/Subdomains を9部門で切る** ＋ 認定/非推奨 ＋ **Pages** ＋ metric view。ここが最大の差別化ポイント（§3.3） |
| 3 | **Lakebase** | ✗ 未充足 | 現場ペルソナのアクション書き戻し（ゲート判断の記録・是正タスク・承認）。synced table で App にサブ秒配信 |
| 4 | **ML / GenAI** | △ Genie のみ | **実モデルが必要**。MLflow モデルを serving endpoint に。推奨は上市初期の需要予測 or 原料ロット→品質逸脱リスク分類。加えて GenAI で Page 自動生成（§4） |
| 5 | **Genie Agent** | △ Genie One だけでは弱い | FAQ は「a real Databricks Genie over your governed tables」と Genie **Agent** を指定。部門別 Genie Agent 9本（各≤50テーブル）＋ 上に Genie One。これが懸念の解にもなる |
| 6 | **Databricks App** | ✗ 未充足 | ペルソナ選択 → その人のオントロジー断面 → 想定質問 → 回答 → Lakebase へアクション書き戻し → カレンダー/Drive 連携 |

### 3.2 4評価ドメインで Exceeds を狙う置き方

4ドメイン（Product / Industry / Build+AI Mindset / Customer Skills）全部が Meets 以上で合格、Exceeds は「箱にチェックを入れた以上のこと」。

**Product** — 新しい面を正しく使っているかが効く。UC セマンティクス（Pages / Domains / metric view / 認定）＋ Genie One ＋ 外部MCPコネクタ ＋ Lakebase ＋ SDP ＋ serving endpoint。
Exceeds の分かれ目は**選ばなかった選択肢を説明できること**。例: なぜ gold テーブルでなく metric view にしたか／なぜ Genie One 単体でなく部門別 Genie Agent を挟んだか／なぜ Zerobus でなく SDP か。判断の記録（ADR形式）を1ファイル置くのが一番安い Exceeds。

**Industry** — 「CPG」でなく「機能性表示食品を既存飲料チャネルに乗せる上市ゲート」まで降りる。語彙で殴る: 機能性表示届出、HACCP/GMP 資格、FEFO、OTIF、ACV/TDP、trade spend 控除、棚替え期、初回配荷。Industry Outcome Map の KPI に接続する。
Exceeds: **部門ごとに違う KPI が1つの意思決定でぶつかる**ことを示す（生産は切替回数を減らしたい／営業は初回配荷を早めたい／財務は在庫を持ちたくない）。CPG を知っている人だけが書ける対立構造。

**Build + AI Mindset** — テキストで読めるエビデンス、自分のコミット、判断の記録。
Exceeds: うまくいかなかったことを書く。「ai_forecast を試したが上市初期はヒストリがなく使えなかったので、類似SKUの立ち上がりカーブを特徴量にした MLflow モデルに切り替えた」のような、捨てた道の記録。

**Customer Skills** — デッキとロールプレイ。buyer の KPI で定量化。
Exceeds: **部長と現場の二層で価値を言い分ける**。部長には意思決定のサイクルタイムと精度、現場には1日の持ち時間。両方を同じ KPI ツリーに繋ぐ。

### 3.3 懸念への技術的な答え — 他人の Page / metric view をどう回避するか

ドキュメントで確認した事実（Genie Ontology / UC semantics / Pages, いずれも2026-10時点）:

- Genie Ontology は **modeled context（metric view / Domains / Pages / 認定）** と **inferred context（既存アセットと利用実績から抽出: metric view・ダッシュボード・SQLクエリ・Genie Agent）** の両方を使う。ユーザーの質問ごとに関連スニペットを retrieval する。
- **スコープを明示的に絞る管理機能は存在しない。** ドメインフィルタ、除外、opt-out は docs に記載なし。効くのは次の3つだけ:
  1. **権限** — スニペットはソースアセットの UC 権限でゲートされる。見えないアセットから抽出した知識は使われない。これが唯一の硬い境界。
  2. **Domain** — Page は domain/subdomain に属し、**Page は domain からアクセスを継承する**（Page 単体に権限を付けない）。curator は `MANAGE DISCOVER` / `MANAGE` を持つ domain 内で統治する。
  3. **認定 / 非推奨** — 認定は Genie One を組織が保証したアセットへ誘導する soft signal。競合定義は非推奨でフェードさせる。
- Genie **Agent** は最大50テーブル/ビューの明示キュレーション。**硬いデータ境界が必要なときは Genie Agent を使う**、と docs が明言している。
- Genie One は回答に引用元を出すので、何が使われたかは検証できる。

**よって推奨は3段構え:**

1. **専用の綺麗な FEVM ワークスペースで作る。** 他人のアセットが存在しない環境にすれば構造的に衝突しない。一番確実で、一番安い。デモの再現性も上がる。
2. **デモは「その部門しか見えない」ペルソナユーザー/グループで実演する。** 権限が唯一の硬い境界なので、部長ユーザーと現場ユーザーに別のグラントを張る。これ自体がガバナンスのデモになる（「営業部長には人事の個人データが見えない」を実演できる）。
3. **部門別 Genie Agent を挟む。** 各部門≤50テーブルで硬く囲い、Genie One はその上で部門横断を担う。「現場＝自部門 Agent、部長＝Genie One で横断」という導線は、スコープ問題への回答であると同時にデモの構成そのものになる。

**そしてこれを隠さず主題にする。** 顧客が全社で Genie One を入れるとき、まさにこの問題（他部署の定義が混ざる）を踏む。詳細は §4。

### 3.4 Google Drive / Calendar 連携 — 事実

- Genie One は外部ソースに繋げる。ホーム画面の検索バー左下の **＋** → ソース選択 → Sign in（OAuth）→ その会話に接続。自動で使われないときは「Google Drive を使って…」と明示的に指示する。
- 利用可能: **Google Drive / Google Calendar / Gmail / Microsoft 365 / Atlassian / Slack / GitHub / Glean(Beta)**。Databricks 提供の MCP で、UC と Unity Gateway で統治。認証はユーザーごと（トークン共有なし）。
- 読み取り系ツールは自動実行、**書き込み系はユーザー承認を挟む**（Allow once / Always allow in this chat / Reject）。
- Genie **Agent** 側の同機能は **Beta**ラベルで、ワークスペース管理者が Previews で「MCP tools in Genie Agents」を有効化する必要がある。**Agent mode 限定**（Chat mode では動かない）。リージョンで Agent mode が使えることが前提。全ユーザーに Workspace access と Databricks SQL access の両エンタイトルメントが必要。
- 制限（デモ設計に効く）:
  - Drive: 25MB上限、**ネイティブの Docs/Sheets/Slides のみ**（PDF・画像・バイナリ不可）。コネクタが作った Doc は編集できるが、外で作った Doc/既存 Sheets/Slides は編集不可。
  - Gmail: 検索・読取・下書きのみ、**送信不可**。
  - Calendar: 検索とイベント作成。書き込みは承認必須。

**デモへの落とし込み（この制限内で成立する動線）:**
- 現場ペルソナ: 「来週の第2ラインで資格が切れる人を出して、代替候補と一緒に、ライン長との15分をカレンダーに入れて」→ UC のデータ＋Calendar 書き込み（承認プロンプトが出るのを**見せる**。ガバナンスの証拠になる）。
- 部長ペルソナ: 「先週の上市ゲート会議の議事録（Drive の Doc）にある前提と、いまの実データの差分を出して」→ Drive 検索 ＋ UC クエリの突き合わせ。**Doc は必ず Google Docs ネイティブで用意する**（PDF は読めない）。
- 「Doc を新規作成してゲート判断サマリを書き出す」はコネクタが作った Doc なので編集もできる。既存 Doc の書き換えに依存する脚本を書かないこと。

### 3.5 エビデンス設計 — 前ビルドの実測から、ここが一番効く

スコアラが読む上限: **30ファイル / 9,000字/ファイル / 合計90,000字**。

前ビルド（`~/fe-bar/cpg-data-trust-cockpit`）の実測:
- `evidence/` 20ファイル、**合計 149,405字**（上限の1.66倍）
- うち `04_graph.json` が単体 38,279字 → 9,000字で切られ、残り29,279字は読まれていない
- `10_ontology_demo_general.txt` 13,735字、`08_native_enablement_general.txt` 10,039字 も切られている
- node_modules を除いた追跡ファイル **117本** → 30ファイル上限を大きく超過

つまり**どのファイルが読まれたかは運任せだった**。これは今回必ず直す。

**今回の設計:**
- ルートに `00_SUBMISSION.md` を置く。読まれる1ファイル目の前提で、全体像・6コンポーネントの充当表・エビデンスへの道案内・自分が決めたこと・借りたものを 9,000字以内に収める。
- `evidence/` は**ちょうど12ファイル以内、各6,000字以内、合計60,000字以内**で設計する（残りを README とコードに空ける）。
- 大きい生成物（グラフJSON・DDL全量・ダッシュボード定義）は `artifacts/` に逃がし、**エビデンスには抜粋と要約統計だけ**を置く。
- DDL 45表は `artifacts/schemas/` に1ファイルで集約し、エビデンス枠から外す。
- `.gitignore` で node_modules を確実に外す（前ビルドは追跡ファイルが膨らんでいた）。

### 3.6 先に潰すリスク（着手順）

| 順 | リスク | 確認方法 | 外れたときの代替 |
|---|---|---|---|
| 1 | **Pages / Domains が Beta** で FEVM で有効化できない | アカウントコンソール Previews を確認（アカウント管理者権限が必要） | Page が使えないと主題が崩れる。代替は metric view の comment ＋ 認定 ＋ Genie Agent instructions で「定義の正本」を表現 |
| 2 | **MCP tools / Agent mode** がリージョンで使えない | ワークスペース Previews ＋ Agent mode の表示を確認 | Drive/Calendar 連携を「あれば大歓迎」のまま諦め、UC 側の価値に寄せる |
| 3 | **前ビルドとの類似判定** | 提出時にナラティブで明示 | シナリオ（上市 vs 欠品）・中核機構（オントロジー統治 vs 関係グラフ）・部門数で差を作る。§4参照 |
| 4 | **FEVM の TTL** がロールプレイ日まで持たない | デプロイ直後に延長申請 | — |
| 5 | **データ生成量**（45表・時系列・連鎖1本） | 最初に1部門で縦に通してから横に広げる | 表数を35に削る。横断の hub 9本は死守 |
| 6 | **serving endpoint の実モデル** | 早めに1本立てる | ai_forecast では「placeholder heuristic」と見なされる懸念。MLflow モデル＋エンドポイントにする |

---

## 4. 「さらに何を作るか」への意見

### 4.1 主題の提案

**「業界データモデルを入れただけでは、Genie One は賢くならない。」**

この一文がデモの背骨になる。理由はこのリポジトリを実際に読んで分かったこと:
- モデルには 13,110 の列COMMENT と 1,136本の横断FK と 92本の metric view が入っている。**意味論は既にある。**
- しかし Genie Ontology が優先的に使うのは Page・認定・Domain という **UC セマンティクス側の資産**であって、テーブルの COMMENT ではない。
- つまり**モデルの意味論を UC セマンティクスへ翻訳する工程**が、丸ごと空いている。ここが顧客の実作業で一番痛むところで、かつ誰も作っていない。

### 4.2 作るもの — 部門間の「同じ言葉・違う意味」を検出して Page に昇格させる層

ユーザーの懸念（他人の metric view / Page が混ざる）を、そのまま製品の中心にする。

- 9部門それぞれに、わざと**衝突する定義**を仕込む。
  - 「売上」= 営業の `sales.order.total_gross_amount`（受注・総額）／財務の `finance.invoice` 純額（計上・返品控除後）／マーケの sell-out（店頭消化）
  - 「稼働率」= 生産の OEE ／保全の設備可用性 ／人事の労働時間稼働
  - 「リードタイム」= 調達の発注〜入荷 ／物流の出荷〜着荷 ／営業の受注〜納品
- 各部門が**自分の metric view とダッシュボードを持つ**状態を作る（＝ inferred context が競合する実環境を再現）。
- **衝突検出**: metric view の YAML・ダッシュボードのSQL・テーブルCOMMENT を GenAI で読み、「同一業務語に複数の計算定義が存在する」箇所を列挙。値の重なりとカーディナリティでデータ側から裏を取る（名前当てを禁止するガードレール）。
- **昇格**: 検出した衝突ごとに、正本の定義・同義語・適用部門・例外を書いた **Page を自動ドラフト生成**し、人が承認して公開。正本の metric view を認定、競合を非推奨にする。
- **実演**: 統治前 → Genie One に「売上」と聞くと部門によって違う数字が返る／引用元がばらつく。統治後 → Page が引用され、認定された metric view が選ばれ、**どの部門のペルソナが聞いても同じ数字**。引用元を画面で見せる。

これは「回避策」ではなく**答え**になっている。顧客が全社 Genie One で必ず踏む問題を、構造として解いている。

### 4.3 前ビルドとの差分（類似判定への備え）

| | 前: CPG Data Trust Cockpit | 今回 |
|---|---|---|
| 課題 | 分析前のデータ探しと目利き（欠品） | 全社 Genie One での定義衝突（新商品上市） |
| 主役 | 需要計画担当者1名 | 9部門 × 部長/現場 の2層 |
| 中核機構 | UC→LLM で**関係グラフ**を生成し人間が差分承認 | metric view/ダッシュボード/COMMENT から**定義衝突**を検出し Page に昇格 |
| 見せる面 | 俯瞰グラフの App | ペルソナ別オントロジー断面 ＋ Genie One ＋ 外部ツール |
| データ | 自作7ドメイン26エンティティ | 業界データモデル ECM 部分集合45表 |
| 外部連携 | なし | Drive / Calendar |

機構が違い、ペルソナ構造が違い、データ基盤が違う。それでも**提出ナラティブに「前ビルドから何を再利用したか」を明記する**。隠すと integrity check の方が先に見つける。

### 4.4 作らないもの（抑制）

- 19ドメイン全部のデプロイ（376表）— 意味論の breadth は Page とオントロジーで示せる。表数で示す必要はない
- 14ペルソナ均等の脚本 — §1.5
- Lakebase Search / ベクトル検索 — Page 検索は Genie One 側が持つ。重複機能を足すと焦点がぼける
- 自作チャットボット — FAQ が「app の chat assistant は Genie の代わりにならない」と明言

---

## 5. 決めてほしいこと

1. **この build は FE Bar の再提出か、顧客デモ資産か、両方か。** 両方なら §3.5 のエビデンス設計と §4.3 の差分明記を最初から組み込む。デモ資産だけなら必須6コンポーネントの縛りが外れ、Genie One ＋ オントロジー ＋ ダッシュボードに集中できる（工数は半分以下）。
2. **ワークスペース** — 新規 FEVM（綺麗な環境＝スコープ問題が構造的に消える）か、既存 `fevm-serverless-rongzi-cpg-general` 再利用（前ビルドの資産とカタログが使える／ただし既存アセットが ontology に混ざる）。推奨は新規。
3. **深掘りする3部門ペア** — §1.5 の案（生産＋人事 / 営業＋財務 / 品質・薬事）でよいか。キリン様など実アカウントの関心に寄せるなら差し替える。
4. **ML モデルの題材** — 上市初期の需要予測 / 原料ロット→品質逸脱リスク / 設備切替リスク、のどれか。
5. **Pages の Beta 有効化**（§3.6 の1番）— これだけは着手前に確認したい。主題が依存している。
