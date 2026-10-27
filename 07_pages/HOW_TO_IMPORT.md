# Page 22本の投入手順（ユーザー作業）

API は**まだ公開されていない**。社内資料（Jesse Kemp「Pre-Built Ontology for Customers」2026-10-15）に
「Pages API は2026年9月末に承認され実装中、10月に出る見込み。Bulk import は今すぐ使える」とある。
実機で `/api/2.0/*/pages` を10通り叩いたが全て Not Found だった。よって **Genie Code の Bulk import** を使う。

## 手順（docs: uc-semantics/pages 準拠）

1. **Discover → Pages → Create page**
2. 右の **Genie Code ペイン**を開き **Bulk import pages** をクリック
3. どのドメインに入れるかを伝える。次のとおり打てばよい：

```
ドメイン「Brickshouse Food and Beverage」とそのサブドメイン（営業 / 財務 / マーケティング）に
既にある22本の Page を、添付した最新の pages_content.md の内容に**置き換えて**ください。
4つのドメインは作成済みで draft ではありません。

ファイルには22本が「## 連番. タイトル」区切りで書かれています。各 Page には
**同義語** / **説明** / **Definition** / **Business use** / **Examples** /
**Related assets** / **Sources** があります。見出しの構成をそのまま使ってください。

守ってほしいこと:
- タイトルは「（Brickshouse ...）」の括弧まで含めてファイルのとおり
- 同義語は1語も足さない。特に Net Sales / Net Revenue / Total Revenue は追加しない
- **本文に Markdown の表を作らない**（箇条書きのまま入れる）
- **金額や比率を補わない。** ファイルに数字が無いのは意図的で、
  用語集に数値を書くとデータ更新のたびに Genie が食い違いを報告するため
- Sources 欄は URL しか入らないので空にして、本文末尾の「## Sources」に書く
- 22本ちょうど。新しい用語を作らない
- ドメインの割り当て:
    「Brickshouse 営業」「Brickshouse 販促」 → 営業
    「Brickshouse 財務」                   → 財務
    「Brickshouse マーケ」                 → マーケティング
    「Brickshouse 全社定義」「Brickshouse 調達」→ 親
```

4. **Attach sources** で `07_pages/pages_content.md` を添付（ローカルファイルで可）
5. 提案された Page を確認。重複・低信頼のフラグを解消する
6. Genie Code が**下書き**としてまとめて作る
7. **ここが重要：全部 Publish する**

## ドメイン4本（2026-10-27 に作り直した）

| tag_key | 名前 | domain_id | draft |
|---|---|---|---|
| `Brickshouse Food and Beverage` | 親 | `755ebf12-1718-4b8c-8eb9-9bc2b3650bea` | false |
| `Brickshouse Food and Beverage/営業` | 営業 | `2e7a6889-45ea-40ef-82a4-57b75bb05269` | false |
| `Brickshouse Food and Beverage/財務` | 財務 | `7209c1c9-0c34-4c9d-93bd-d039726eddef` | false |
| `Brickshouse Food and Beverage/マーケティング` | マーケティング | `04be6f8f-405f-4d82-a492-88c9fae8c232` | false |

**一度消えている。** 10/25 に作ったものは Genie Code が「存在しない」と言ってきた時点で
アカウントの一覧（985件）から消えていた。tag policy の方は4本とも残っていたので、
**消えたのは domain だけ**。当時 `--draft` で作っていたことが原因と見ている
（アカウントがドメイン上限に張り付いていたので、誰かが下書きを掃除した可能性が高い）。
作り直すときは `--draft` を付けない。

```bash
databricks domains create-domain "Brickshouse Food and Beverage" \
  --name "Brickshouse Food and Beverage" --subtitle "..." --description "..."
databricks domains create-domain "Brickshouse Food and Beverage/営業" \
  --name "営業" --parent-domain-id <親のid> --subtitle "..."
```

枠が空いていたので（985/1000）、**マーケティングもサブドメインとして作れた**。
10/25 時点では上限で作れず「タグのみ」だったが、3部門すべてが本物のサブドメインになった。

## 書式を実機のお手本に合わせた（2026-10-27）

他のFEの Page（`Attrition rate (Current network)`）を見て、想定していた書式と
違うことが分かったので22本を書き直した。

| 項目 | お手本 | 直す前のうち |
|---|---|---|
| 数値 | **ゼロ**。式と条件だけ | 金額・比率が散在 |
| Definition | **1行の式** | 段落＋表 |
| Business use | **箇条書き3行** | 段落＋Markdown表 |
| Examples | **想定質問1つ** | **無かった** |
| 長さ | 画面1枚 | 画面2〜3枚 |

効いているのは2つ。**`MEASURE(total_net_amount)` のように metric view の組み方を書く**こと
（「この表を使え」では Genie が組み立てを推測する）。そして **Examples に実際の質問文を置く**こと。

本文から Markdown の表を全部外した。お手本に表が無いこともあるが、
Discover の Page 一覧が「読み込みに失敗しました」になった障害の原因候補でもある。

## なぜ Publish が必須か

docs の記述：
> Published Pages are available in all Genie One conversations.
> Draft Pages are available only in conversations with the Page owner.

下書きのままだと**あなたの会話でしか効かない**。デモで他の人の画面に出ない。
また Page は**ドメインからアクセスを継承する**ので、公開するとドメインを見られる人全員が読める。

## 投入後に確認してほしいこと（これが今回の一番の見せ場になる）

Genie One で **「売上」** と1語だけ入れて、10/26 の結果と比べてください。

| | 10/26（Page なし・実測済み） | 投入後（期待） |
|---|---|---|
| 引いた Page | 他FEの `純売上` / `Net Revenue` / `Net Sales` / `Total Revenue` | `売上（Brickshouse 全社定義）` |
| 使ったテーブル | `samples.bakehouse.sales_transactions` | `finance_mart.finance_ar_invoice` |
| 答え | 66,471（2024年5月のベーカリー） | 約 1,286 億円（2026年の Brickshouse 純売上） |

**10/26 の画面はもう撮れている**ので、投入後に同じ質問をすれば before/after が1枚で並びます。
FE Bar にはこの2枚を出します（顧客デモには出しません。§6 のとおり誤答は顧客に見せない）。

## 先にやってほしいこと

Bulk import の前に**ワークスペース命令**を入れてください（別途お渡しした文面）。
Page はアカウント共有で他人の Page と競合しますが、ワークスペース命令は
**このワークスペースにしか効かない**ので、他者に漏れずに強く誘導できる唯一の手段です。
Genie Agent には効かないので、Agent 側はこちらで `apply_instructions.py` が入れています。

## 権限（docs 準拠）

- Page の作成・公開は **Consumer** でも可能
- 下書きの編集・公開は **Page の所有者または curator** のみ
- curator = アカウントレベルの `MANAGE DISCOVER`、またはドメイン/サブドメインの `MANAGE`
- **アカウント管理者とワークスペース管理者は自動で `MANAGE DISCOVER` を持つ**
- Page を作るには**ドメインが1つ以上必要** → 作成済み（親＋営業＋財務）
