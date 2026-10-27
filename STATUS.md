# 実機の確定事項と未決事項

> **これは 2026-10-25 時点の着手前メモで、最終成果と食い違う箇所がある。**
> 確定した仕様・数字は `00_SUBMISSION.md`（結論）と `BUILD_LOG.md`（全工程）が正。
> 特にこのメモの後で変わった点: 部門は9→**4**（営業/財務/マーケ/横断）、
> ドメイン上限で作れなかった subdomain は枠を空けて**営業・財務の2本を作成済み**、
> テーブルは24→**30**（マーケ6本追加）。


最終更新 2026-10-25 / ワークスペース `fevm-serverless-rongzi-cpg-general` / カタログ `rongzi_catalog_dev`

## 確定した制約（実測・docs と食い違う点を含む）

| 項目 | 実測 | docs の記載 | 影響 |
|---|---|---|---|
| governed tag（tag policy） | **3,074 で上限到達**。新規作成が `maximum number of tag policies allowed is reached` で失敗 | 1,000 / account（fixed） | ドメインを作る前提が崩れる |
| domain + subdomain | **1,000 / 1,000 で上限到達**。`has reached the maximum allowed number of domains (1000)` | 300 / account（fixed） | **subdomain 3本が作れなかった** |
| 自分が回収できたドメイン枠 | **1枠のみ**（`Bricks Beverage セールス`） | — | 親ドメイン1本で打ち止め |
| 自分が owner のドメイン | **0件**（owner_ids に自分の id が無い。`SwedBricks` は他者、`Wanderbricks` は owner 未設定で自分のものと断定できない） | — | これ以上の回収は不可 |

### 判明した仕様（docs に書かれていない挙動）
- **UC Domain を作るには同名の governed tag policy が先に必要。** 無いと `create-domain` が `Tag policy with name ... not found` で失敗する
- **tag policy を削除すると、対応する domain も連鎖削除される。** `Bricks Beverage セールス` の tag policy を消したら domain も消えた（domain の直接削除は `Not Found` を返していた）
- **governed tag は許可値（allowed values）を持てる。** 上限は 500値/タグ。`system.certification_status` が `certified` / `deprecated` の2値を持つ実例

## 確保済みの資産（4枠）

| tag_key | 用途 | 状態 |
|---|---|---|
| `Brickshouse Food and Beverage` | 親ドメイン（全 Page の置き場） | tag policy ＋ **domain 作成済み（draft）** id `3793bb10-d42a-47a4-b422-ebb52d01c1d0` |
| `brickshouse_department` | 部門区分（9許可値: 営業/マーケティング/研究開発/生産/品質薬事/調達/物流SCM/財務/人事） | tag policy 作成済み。**subdomain の代替** |
| `Brickshouse Food and Beverage/サプライチェーン` | 予備枠（上限アカウントなので手放さず保持） | tag policy のみ（domain 不可） |
| `Brickshouse Food and Beverage/コーポレート` | 予備枠 | tag policy のみ（domain 不可） |

## ドメイン設計の修正 — subdomain を governed tag に置き換える

当初案（親1 + subdomain 3）は**ドメイン上限で不可**。代替:

```
Brickshouse Food and Beverage          ← domain 1本。Page は全部ここに置く
  └─ 全 Page: 売上 / 在庫 / リードタイム / 商品 / 得意先 / 従業員
             OTIF / FEFO / OEE / 逸脱 / CAPA / 配下率 / 粗利 / 要員充足率 …
             （Page タイトルと同義語に部門名を入れて識別する）

brickshouse_department = 営業 | マーケティング | ... ← governed tag。18スキーマに付与
  └─ Discover / Catalog Explorer の部門フィルタはこれで効かせる
```

**失うもの**: Discover 上で9部門が subdomain として並ぶ見た目、部門ごとの `MANAGE` 委譲（デモでは不要）。
**失わないもの**: Page による定義の正本化（主題の心臓部）、部門別の絞り込み、部門別の Genie Agent 9本・ダッシュボード 9本・Grant による部門分離。

> 主題（部門間の定義衝突 → Page に昇格）は**衝突する語がそもそも全社語**なので、親ドメイン1本に置くのが元々正しい。実質的な損失は小さい。

## 確認済みの良い知らせ

- cpg-general から見えるカタログは **5件のみ**（`rongzi_catalog_dev` / `fevm_shared_catalog` / `samples` / `system` / `__databricks_internal`）→ **他FEの metric view・ダッシュボード・クエリ・Genie Agent は届かない**
- `rongzi_catalog_dev` は空（`default` と `information_schema` のみ、テーブル0件）
- 残存ダッシュボード 0件 / 残存 Genie space 0件 → ワークスペースは綺麗
- 社名 `Brickshouse Food and Beverage` は domain 1,000件・tag policy 3,074件と衝突なし。既存の Databricks デモ社名ファミリー（`Brick Health` / `Brick Pharma` / `BrickCommerce` / `BrickMobile`）にも整合

## 未確認（API では取れない。UI で見る必要がある）

| # | 確認対象 | 場所 | 外れたときの代替 |
|---|---|---|---|
| 1 | **Pages** が有効か | アカウントコンソール → Previews | Page が使えないと主題が成立しない。metric view comment ＋ 認定 ＋ Genie Agent instructions に寄せる |
| 2 | **MCP tools in Genie** / **Agent mode** が有効かつリージョン対応か | ワークスペース設定 → Previews（「MCP tools in Genie Agents」）／Genie One のチャット欄に ＋ アイコンが出るか | 「同僚として使う」ビート4が落ちる。UC 側の価値に寄せる |
| 3 | **ダッシュボードが Genie の引用に出るか** | 実機で1本作って質問を投げ、引用元を見る | 「ontology の snippet になる」の表現を「文脈として効く」に弱める |

---

## ドメイン方針（確定）

### 方針: 親ドメイン1本で完結させる。追加枠は取りに行かない。

アカウントは `1000/1000` で、自分が owner のドメインは0件＝回収できる枠がない。
他FEの junk ドメイン（`Test` / `test domain` / `tire_demo` / `Demo Domain` / `BakehouseDomainTest2` / draft 69件）を消せば空くが、**他人の資産なので触らない**。空き枠を監視して奪い合うのも同僚に対して筋が悪いのでやらない。

### 1. Page は全部 `Brickshouse Food and Beverage` に置く

subdomain が無いので、**Page のタイトルと同義語で部門を識別する命名規約**を置く。
これは妥協ではなく、retrieval 上むしろ有利（部門名が固有名詞として効き、同業55社の Page に勝ちやすい）。

| 種別 | タイトル規約 | 同義語に入れるもの | 例 |
|---|---|---|---|
| **全社語**（部門間で衝突する語＝主題の中心） | `<語>（Brickshouse 全社定義）` | **各部門の呼び方を全部** | 「売上（Brickshouse 全社定義）」 ← 同義語: 受注金額 / 計上売上 / 純売上 / 店頭消化 / Brickshouse の売上 |
| **部門語** | `<語>（Brickshouse <部門>）` | その部門の言い回し | 「OTIF（Brickshouse 物流SCM）」「配下率（Brickshouse 営業）」 |

全社語（親に置くべきもの）: 売上 / 在庫 / リードタイム / 商品(SKU) / 得意先 / 従業員
部門語: 受注 / 配下率 / メディアROI / OEE / 切替ロス / OTIF / FEFO / 逸脱 / CAPA / 粗利 / 販促費控除 / 要員充足率 / 食品衛生資格 …

### 2. 部門の絞り込みは governed tag と Page のリンクで代替する

- **`brickshouse_department`**（許可値9: 営業/マーケティング/研究開発/生産/品質薬事/調達/物流SCM/財務/人事）を各部門スキーマに付与
  → Discover / Catalog Explorer で部門別に絞れる（subdomain フィルタの代替）
- **Page の `related assets` / `sources`** にその部門のテーブルと metric view を紐づける
  → 部門の資産から Page へ、Page から部門の資産へ双方向に辿れる

### 3. draft で作り、公開は実演方法を決めてから

- draft ドメイン＝キュレーター（自分）にしか見えない。draft Page＝owner のみ
- **自分のアカウントでペルソナを演じるなら draft のままで足りる**（他FEに一切見えず、汚染も与えない）
- **ペルソナ用のグループユーザーで実演するなら公開が必要**。公開すると他FEにも見えるが、社名が固有名詞なので混乱は小さい
- → 実演方法の決定が、公開タイミングの判断になる

### 4. 予備 tag policy 2枠は「subdomain の予約」として保持する

`Brickshouse Food and Beverage/サプライチェーン` と `/コーポレート` は tag policy だけ存在し domain が無い状態。
手放すと上限アカウントなので他FEに取られて戻らない。保持しておけば、**ドメイン枠が1つでも空いた瞬間に `create-domain` だけで subdomain 化できる**（tag policy 作成の順番待ちが不要）。これが保持する理由。

### 5. エスカレーションは出す（並行・ブロッカーではない）

成功すれば subdomain 3本に戻せる。出す内容:
- domain `1000/1000`、tag policy `3074` で**到達は 2026-10-25**（直近7日で103件作成、今日3件で満杯）
- docs の記載は domain 300 / governed tag 1,000 で**実際の強制値と食い違う**
- junk/draft の棚卸し、または上限引き上げの依頼
- 宛先: `metastore_admins` / `#fe-specialization`

### 失うものと失わないもの

| | |
|---|---|
| **失う** | Discover 上で9部門が subdomain として並ぶ見た目。部門ごとの `MANAGE` 委譲（デモでは不要） |
| **失わない** | Page による定義の正本化（**主題の心臓部**）／部門別の絞り込み／部門別 Genie Agent・ダッシュボード・Grant による部門分離／衝突検出→Page 昇格のループ |

---

## Genie One に自分のオントロジーを優先させる方法（docs 確認済み・2026-10-25）

### レバー1（最強）: Genie Agent の自動ルーティング — ワークスペース境界が効く
docs（Chat in Genie One）: 「It searches available Genie Agents for one relevant to your question」。マッチする Agent があればそれが答え、無ければデータ資産を直接探す。
**ルーティング候補はワークスペース内の Genie Agent のみ**＝他FEの Agent は別ワークスペースなので入らない。
→ **部門別 Genie Agent を作ること自体が「自分の資産を優先させる」手段**になる。Genie One から Agent を呼ぶのは設計どおりの動きで、しかも自動。

⚠ docs の注意書き: 「Workspaces with many Genie Agents might experience reduced routing accuracy」
→ **Agent を増やすとルーティング精度が落ちる。** 第1弾の4本（部門3＋横断1）は精度面で有利。9部門に広げるときは誤ルーティングの検証が必要。

### レバー2: Workspace instructions — 唯一の明示的な steering
docs: 「Admins can add instructions that apply to all chat conversations in the workspace. These don't affect Genie Agents.」
→ ワークスペース全体のチャットに効く指示を書ける。例:
> 「業務用語は `Brickshouse Food and Beverage` ドメインの Page を正本とする。他社名・他ドメインの定義は使用しない。売上・在庫・リードタイムは必ず Brickshouse の全社定義 Page を参照する。」

Genie Agent には効かないので、**Agent 側は instructions（100件/space まで）に別途書く**。

### レバー3: authority score の3入力を操作する
docs（Genie Ontology）: 「Each snippet gets an authority score based on **where it was generated from, how often it is used, and how fresh it is**.」

| 入力 | 操作方法 |
|---|---|
| **origin（生成元）** | 定義を Page と metric view（human-modeled layer）に置く。ダッシュボードや SQL からの推論より上位の出自にする |
| **usage frequency（使用頻度）** | **デモ前に自分の資産を使い込む。** リハーサルで質問を繰り返す、ダッシュボードを開く、metric view をクエリする。完全に自分で制御できる |
| **freshness（新しさ）** | **デモ直前に Page とテーブルを更新する。** update_time を新しくする |

### レバー4: 固有名詞で relevance を取る
docs: 「Genie ranks the most relevant snippets, resolves conflicts」。relevance は prompt との一致。
→ `Brickshouse` ＋部門名を **Page タイトル・同義語・デモ質問文**の全部に通す。同業55件（Utz / McCormick / ferrero / Diageo / Heineken / Unilever CPG など）の Page に勝つ。

### 存在しないもの（確認済み）
- native chat に **スコープ指定・ドメイン限定・資産指定・Agent ピッカーは無い**
- snippet を閲覧・編集・承認・却下する UI は無い
- 認定が snippet のランキングにどう効くかは docs に記載が無い（「組織が保証した資産へ誘導する」までの表現）

### 裏技: 完全な決定性が必要なら Slack / Teams 経由
Slack・Teams の Genie アプリは channel 単位で **Genie scope → 特定の Genie Agent をピン留め**できる。
ピン留めすると**その Agent にしかルーティングされない**。native chat には無い機能。
→ 顧客デモで「毎回確実に同じ答え」が要る場面は Slack 経由にする選択肢がある。

### 検証（データができたら必ずやる）
1. Page を1本作り「売上」のような一般語で質問 → **引用アイコンで他FEの Page が出るか**を見る
2. 部門質問が意図した Agent にルーティングされるか（Agent 10本に増やす前と後で比較）
3. Workspace instructions の有無で回答が変わるか
