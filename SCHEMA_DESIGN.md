# 単一カタログでの スキーマ / ドメイン設計

> **これは 2026-10-25 時点の着手前メモで、最終成果と食い違う箇所がある。**
> 確定した仕様・数字は `00_SUBMISSION.md`（結論）と `BUILD_LOG.md`（全工程）が正。
> 特にこのメモの後で変わった点: 部門は9→**4**（営業/財務/マーケ/横断）、
> ドメイン上限で作れなかった subdomain は枠を空けて**営業・財務の2本を作成済み**、
> テーブルは24→**30**（マーケ6本追加）。


対象: `rongzi_catalog_dev`（ワークスペース `fevm-serverless-rongzi-cpg-general` / ws_id 7474658774258275）
前提確定日 2026-10-25（すべて実機で実測）

---

## 0. 実測した現状

| 項目 | 実測値 |
|---|---|
| メタストア | `metastore_aws_us_east_1`（id `c0da88f1…`、owner `metastore_admins`、us-east-1）= **FEVM 共通** |
| カタログ | `rongzi_catalog_dev`（`ISOLATED`、bind 先は 3 ワークスペース: `2566369376390219` / `7474658774258275`(cpg-general) / `7474659203415319`) |
| カタログ内の現状 | スキーマは `default` と `information_schema` **のみ、テーブル0件**。削除は完全に効いている |
| ワークスペースから見えるカタログ | **7件のみ**（`rongzi_catalog`, `rongzi_catalog_dev`, `rongzi_serverless_fevm_aws_catalog`, `fevm_shared_catalog`, `samples`, `system`, `__databricks_internal`）。**他FEのカタログは一切見えない** |
| アカウント内のドメイン数 | **1,000件**（top-level 556 / subdomain 444）。docs の上限表記は 300/account |
| 食品・飲料・CPG 隣接ドメイン | **55件**（Utz Quality Foods, McCormick, ferrero_data, Diageo, Heineken×3, Haleon, Unilever CPG Intelligence, Blue CPG Company, Bakehouse×8, FreshestFoodsGroceries, Siam Basket Retail, coty_supply_chain, Restaurant Operations, SGWS Commercial, JTI×2, PMI_Sales …） |
| 自分の前ビルド残骸 | ドメイン `Bricks Beverage セールス`（2026-08-27作成）がアカウントに残存。ほか `SwedBricks` / `Wanderbricks` |

### 部門名はすべて取られている（実測）

`Sales` / `Finance` / `finance` / `Marketing` / `HR` / `Manufacturing` / `Procurement` / `Product` / `Customer` / `customer` / `quality` / `production` が top-level に既存。さらに `ferrero_data/Sales`, `Utz Quality Foods/Manufacturing`, `McCormick/Finance`, `Haleon/Finance`, `aoba_seiki/quality`, `Iscar/Production` …といった同名 subdomain が多数。
**「営業」「財務」のような素の部門名でドメインを作ることは不可能。**

---

## 1. 汚染の実像 — 心配は半分当たり、半分は構造的に防げている

ユーザーの懸念は「他ワークスペースの Pages と metric view が ontology に影響する」。実測で切り分けると:

| ontology への寄与源 | スコープ | 他ワークスペースから届くか | 根拠 |
|---|---|---|---|
| **Pages** | **アカウント** | **届く** | Page は domain に属し domain からアクセスを継承。公開済み Page は全会話で利用可能 |
| **Domains / subdomains** | **アカウント** | **届く** | docs 明記: 「Domains that you configure apply to the whole account, not select workspaces」。実測1,000件 |
| metric view | カタログ内 | **届かない** | カタログ可視性が7件のみ。他FEのカタログは bind 外。`ISOLATED` の非 bind ワークスペースは明示グラントがあってもエラー、information_schema にも出ない |
| ダッシュボード | ワークスペースオブジェクト | **届かない** | 他FEのワークスペースのメンバーでない |
| SQLクエリ（query history） | ワークスペースオブジェクト | **届かない** | 同上 |
| Genie Agent | ワークスペースオブジェクト | **届かない** | 同上 |

**結論: 露出は Pages と Domains の2つだけ。metric view は既にカタログ分離で守られている。**
これは重要で、対処すべき面が1/5に絞れる。ただし Pages には除外機能が存在しない（docs にスコープ指定・除外・opt-out の記載なし）ので、**消すのではなく retrieval で勝つ**設計にする。

### 本当に効く対処（優先順）

1. **固有名詞で勝つ。** 架空社名を決め、**ドメイン名・Page タイトル・Page の synonyms・デモの質問文**の全部に入れる。Genie の retrieval は prompt relevance を見るので、「<社名>の売上定義」は `ferrero_data/Sales` の Page より必ず上に来る。これが唯一かつ最強の武器。
2. **自分の過去ドメインを片付ける。** `Bricks Beverage セールス` は同じ飲料業界＝最も競合する。削除または改名。**今すぐできる、効果の大きい1手。**
3. **現場デモは Genie Agent で、部長デモだけ Genie One で。** Agent は最大50オブジェクトの明示キュレーション＝硬い境界。汚染が起きうる面をデモの一部だけに閉じ込める。
4. **認定（certify）を自分の metric view / テーブルに付ける。** 届く範囲（自カタログ）では自分だけが認定済みになる。
5. **リハーサルで引用元を必ず見る。** Genie One は引用を返す。他社 Page が引かれた質問は、固有語を足して言い直す。これを本番前チェックリストにする。

### 先に確認が必要な2点

- **ドメイン作成が通るか。** docs の上限は 300/account、実測は 1,000件。上限の解釈が違う可能性が高いが、**最初に1本 create-domain して通ることを確認**する。ここで詰まると設計の前提が崩れる。
- **cpg-general 側のカタログ可視性。** 上記7件は `fevm-rongzi-serverless` から見た数字（cpg-general は認証切れで未確認）。同じ FEVM パターンなので同様の見込みだが、再認証後に `databricks catalogs list` で確認する。
- **前ビルドのワークスペースオブジェクト。** cpg-general に残っている可能性があるもの: Genie space `01f1a661cddd180999d0bc372cf436f4`、JPダッシュボード `01f1a663e46711548cec32b8b8aec33f`、監視ダッシュボード4本。これらは**自分のワークスペースなので ontology に効く**。削除する。

---

## 2. 設計を縛る一番のルール — ドメインタグは継承し、剥がせない

docs の仕様:
> カタログまたはスキーマにドメインタグを付けると、含まれるテーブル等の資産がそれを継承する。**継承されたドメインタグは個別資産から外せない。**

ここから2つの帰結が出る。

**(a) カタログにドメインタグを付けてはいけない。** 1カタログしかないので、付けた瞬間に全22スキーマ・全テーブルが1ドメインに固定され、二度と剥がせない。

**(b) 層（bronze/silver/gold）をスキーマの第一軸にしてはいけない。** `silver` スキーマにドメインタグを付けると9部門全部が同一ドメインになる。前ビルドの `cpg_bronze` / `cpg_silver` / `cpg_gold` 構成は、**今回の要件（部門＝ドメイン）とは両立しない。**

→ **スキーマの第一軸は部門。層は第二軸（接尾辞）。**

---

## 3. スキーマ構成

```
rongzi_catalog_dev
│
│  ■ 取込層 — ソースシステム単位（部門では切らない）/ ドメインタグなし
├── ops_landing            Volume `raw` + 生テーブル
│                          例: sap_vbak_raw, mes_batch_raw, wms_txn_raw, workday_worker_raw,
│                              nielsen_pos_raw, edi_852_raw, lims_result_raw
│
│  ■ 部門層 — 9部門 × 2スキーマ
├── sales_core      sales_mart         営業
├── marketing_core  marketing_mart     マーケティング
├── rnd_core        rnd_mart           研究開発
├── mfg_core        mfg_mart           生産
├── quality_core    quality_mart       品質・薬事
├── procure_core    procure_mart       調達
├── scm_core        scm_mart           物流・SCM
├── finance_core    finance_mart       財務
├── hcm_core        hcm_mart           人事
│
│  ■ 横断・運用層
├── xdept_mart             部門横断マート（FE Bar の "integrated" の証拠）
├── semantics_ops          定義衝突検出結果・Page下書き・認定台帳（GenAI出力）
└── platform_ops           パイプライン実行ログ・expectations集計・鮮度・監視
```

合計 **22スキーマ**（上限は10,000/カタログなので余裕）。

### `_core` / `_mart` にした理由（`_silver` / `_gold` にしない）

- Genie の引用にはテーブル名がそのまま出る。**顧客デモで `cpg_silver.xxx` が画面に出るのは避けたい**（層は業務ユーザーに見せない、という自分の方針と整合）
- メダリオンは**スキーマ名ではなく Lakeflow パイプライン定義と `platform_ops` のリネージで証明する**。FE Bar の評価者には README に対応表を1行で書けば十分
- `_core` = 整形済み conformed（industry data model のテーブル）、`_mart` = 用途別集計＋metric view

> README に必ず書く1行: `ops_landing = bronze / *_core = silver / *_mart + xdept_mart = gold`

### 取込層をソースシステム単位にした理由

Bronze は業務部門の形をしていない。SAP の1本の抽出が営業と財務の両方に流れるのが現実。
**取込はソースの形、`_core` 以降は業務の形**——この境界線がそのまま「Lakeflow が何をしているか」の説明になる。ドメイン分類からも自然に外れる（業務ユーザーに見せない層なので）。

### テーブル配置

| スキーマ | 中身 | 目安本数 |
|---|---|---|
| `ops_landing` | ソース単位の生テーブル | 12〜15 |
| `<dept>_core` | industry data model（ECM）から抜いた conformed テーブル | **各6〜8本** |
| `<dept>_mart` | 用途別マート 2本 + metric view 3本 | 各5 |
| `xdept_mart` | 横断マート 4〜6本 | 4〜6 |
| `semantics_ops` | `definition_conflicts`, `page_drafts`, `certification_ledger`, `ontology_run_log` | 4 |
| `platform_ops` | `pipeline_events`, `expectation_results`, `table_freshness`, `grant_snapshot` | 4 |

**`_core` を 6〜8本/部門（計 60〜70本）に増やした理由**: 顧客デモを部門ごとに独立させる方針になったため、各部門が単独で質問に耐える厚みが必要。前回案の45本では1部門5本しかなく、独立デモが成立しない。横断用の hub 9本（`workforce.employee` / `product.sku` / `customer.account` / `procurement.supplier` / `finance.cost_center` / `manufacturing.plant` / `research.rd_project` / `regulatory.product_registration` / `marketing.brand`）は**必ず全部入れる**。これが欠けると横断が死ぬ。

---

## 4. ドメイン構成 — 親1本 + subdomain 9本

アカウントに1,000件あり部門名が全部取られているので、**固有の社名を親にして subdomain で部門を切る**。これならアカウントへの追加は10件で済み、全 tag_key が衝突しない。

```
<社名>                                   ← top-level domain（1本）
├── <社名>/営業          tag → sales_core, sales_mart
├── <社名>/マーケティング   tag → marketing_core, marketing_mart
├── <社名>/研究開発        tag → rnd_core, rnd_mart
├── <社名>/生産           tag → mfg_core, mfg_mart
├── <社名>/品質・薬事      tag → quality_core, quality_mart
├── <社名>/調達           tag → procure_core, procure_mart
├── <社名>/物流・SCM      tag → scm_core, scm_mart
├── <社名>/財務           tag → finance_core, finance_mart
└── <社名>/人事           tag → hcm_core, hcm_mart
```

仕様上の注意（docs 準拠）:
- subdomain のネストは**1段のみ**。subdomain の中に subdomain は作れない
- tag_key は `{親タグ}/{subdomain名}` 形式。**subdomain 名にスラッシュは使えない**（`物流・SCM` は中点なのでOK、`物流/SCM` は不可）
- **親タグと subdomain タグは独立。** `<社名>/営業` を付けても `<社名>` は付かない。Discover の閲覧上は subdomain の資産が親にもロールアップする
- ドメインへの資産追加は**そのドメインの governed tag を資産に付ける**こと。スキーマに付ければ配下テーブルが継承する
- 下書きドメインはキュレーターにしか見えない。**公開するまでは他FEから見えない**ので、作りかけの間は安全

`xdept_mart` は `<社名>` 親タグを直接付ける（部門に属さない横断資産）。
`ops_landing` / `semantics_ops` / `platform_ops` は**タグを付けない**（業務ドメインではない）。

### 社名の候補（アカウント内で未使用を実機確認済み）

`Seiryu Beverages` / `蒼流ホールディングス` / `Sekirei` / `Suzuran` / `Hoshizaki` / `Ryusen` — いずれも1,000件のドメインと衝突なし。
`Bricks Beverage` は前ビルドで使用済み＆アカウントに残存しているので**使わない**（類似判定と汚染の両方で不利）。

推奨: **`Seiryu Beverages`（蒼流ビバレッジ）** — ビール・飲料・健康食品の3事業を持つ架空の日本企業。英字表記なので tag_key が安全、かつ日本語デモでも「蒼流」で通る。

---

## 5. Grant 設計 — これ自体がデモになる

グループを作って層と部門の2軸で切る。「同じ質問を2人のペルソナに投げると違う答えが返る」を実演できる。

| グループ | 権限 | 誰 |
|---|---|---|
| `seiryu_platform` | カタログ ALL PRIVILEGES | 基盤担当（自分） |
| `seiryu_exec` | 全 `*_mart` + `xdept_mart` に SELECT | 各部門長（横断が見える） |
| `seiryu_<dept>_biz` | `<dept>_mart` のみ SELECT | その部門の現場 |
| `seiryu_<dept>_analyst` | `<dept>_core` + `<dept>_mart` に SELECT | その部門のアナリスト |

**仕込む1点**: `hcm_core` / `hcm_mart` は `seiryu_exec` と人事グループにのみ SELECT。
→ 営業部長が「うちのチームで資格が切れる人は？」と聞くと答えられない。人事部長なら答えられる。**Genie One が UC 権限を本当に尊重していることを、画面で証明できる。** これはセキュリティ質問に必ず出るので、デモの資産価値が高い。

`ops_landing` / `platform_ops` / `semantics_ops` は `seiryu_platform` のみ。業務ペルソナには存在ごと見せない（`BROWSE` も付けない）。

---

## 6. Genie Agent / メトリックビュー / ダッシュボードの配置

| 資産 | 単位 | 参照範囲 | 上限 |
|---|---|---|---|
| **Genie Agent** | 部門ごと 9本 | `<dept>_core` + `<dept>_mart`（約12オブジェクト） | 50オブジェクト・100 instructions / space |
| **Genie Agent（横断）** | 1本 | hub 9本 + `xdept_mart` + 共通 metric view（約20） | 同上 |
| **metric view** | `<dept>_mart` 内 | 部門ドメインタグを継承 | 各部門3本 = 27本 |
| **AI/BI ダッシュボード** | 部門ごと 9本 | `<dept>_mart` のみ参照 | — |
| **Genie One** | ワークスペース共通 | 部長ペルソナの横断デモ専用 | — |

**顧客デモの導線（部門ごとに独立）**: 部門 Genie Agent → その部門のダッシュボード → 現場アクション（Lakebase 書き戻し）。1部門で完結し、他部門に依存しない。
**FE Bar の導線（統合）**: Genie One ＋ `xdept_mart` ＋ 定義衝突の統治層。これが「disconnected pieces ではない」の証明になる。

27本の metric view のうち**3組は意図的に定義を衝突させる**（`sales_mart.revenue` = 受注総額 / `finance_mart.revenue` = 計上純額 / `marketing_mart.revenue` = 店頭消化）。`semantics_ops.definition_conflicts` がそれを検出し、Page に昇格させる。

---

## 7. 作る順番（詰まる所を先に潰す）

| 順 | やること | 詰まったら |
|---|---|---|
| 0 | `databricks auth login --profile fe-vm-serverless-rongzi-cpg-general` | — |
| 0 | cpg-general で `catalogs list` し、見えるカタログが7件程度か確認 | 他FEのカタログが見えたら metric view 汚染も対処対象に加わる |
| 0 | **`create-domain` を1本試して通るか確認**（上限1,000/300問題） | 通らなければドメイン無しで metric view comment + 認定 + Agent instructions に寄せる |
| 0 | 前ビルド残骸の削除: ドメイン `Bricks Beverage セールス`、cpg-general の Genie space `01f1a661cdd…`、ダッシュボード `01f1a663e46…` と監視4本 | — |
| 0 | Previews で Pages / Domains / MCP tools / Agent mode の有効化を確認 | §PLAN.md 3.6 の代替に切替 |
| 1 | 22スキーマ ＋ Volume `ops_landing.raw` 作成 | — |
| 2 | ECM から 60〜70テーブルを抜いて `_core` の DDL を生成（カタログ名置換・hub 9本必須） | — |
| 3 | 合成データ生成 → `ops_landing.raw` に着地 | — |
| 4 | Lakeflow SDP: landing → `_core`（expectations・PK/FK）→ `_mart` / `xdept_mart` | — |
| 5 | ドメイン1本 + subdomain 9本作成、スキーマにタグ付け（**カタログには付けない**） | — |
| 6 | metric view 27本（衝突3組込み）、認定、グループと Grant | — |
| 7 | Genie Agent 10本、ダッシュボード9本 | — |
| 8 | 定義衝突検出 + Page 自動ドラフト（`semantics_ops`） | — |
| 9 | Lakebase（現場の書き戻し）、ML serving endpoint、App | — |
| 10 | エビデンス収集（30ファイル / 9,000字 / 90,000字 の枠内） | — |

---

## 8. 前ビルドの構成からの変更点（なぜ変えたか）

| | 前ビルド | 今回 | 理由 |
|---|---|---|---|
| スキーマ第一軸 | 層（`cpg_bronze`/`cpg_silver`/`cpg_gold`） | **部門** | ドメインタグがスキーマから継承され剥がせないため、層を第一軸にすると9部門が1ドメインに潰れる |
| 層の表現 | スキーマ名 | 接尾辞 `_core`/`_mart` ＋ パイプライン定義 | 顧客デモで層名を見せないため |
| 取込層 | 層単位 | **ソースシステム単位** | 現実の形。かつドメイン分類から自然に外れる |
| ドメインタグ | `cpg_domain` カスタムタグ7種 | **UC Domain 親1本 + subdomain 9本** | Genie Ontology が使うのは UC Domain。カスタムタグでは効かない |
| ドメイン命名 | `Bricks Beverage セールス` | `Seiryu Beverages/営業` | アカウント1,000件・部門名全取られ・同業55件との衝突回避 |
| Genie | 1スペース | 部門9 + 横断1 | 顧客デモの独立性 ＋ 汚染を閉じ込める硬い境界 |
