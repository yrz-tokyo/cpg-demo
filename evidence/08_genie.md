# Genie Agent — 部門別4本と、統治の出し入れ

## 構成

| Agent | オブジェクト数 | 中身 |
|---|---|---|
| **Brickshouse 営業** | **30** | 受注・請求・得意先・営業担当・地域・店頭実売・配下店舗 ＋ **販促**（イベント・明細・精算・原資・引当・控除）＋ ブランド・キャンペーン |
| **Brickshouse 財務** | 15 | 売掛・買掛・勘定・原価センター・利益センター・標準原価 ＋ 得意先・受注・SKU |
| **Brickshouse マーケティング** | 15 | ブランド・キャンペーン・媒体費・配信執行・消費者調査・syndicated ＋ POS・SKU・販促明細 |
| **Brickshouse 全社横断** | 18 | 各部門の metric view と silver を hub キーで貫く |

## 販促を営業に入れた理由（測定で分かったこと）

フェーズ1では営業 / 財務 / 販促 / 横断の4部門に分けていた。そのとき **`trap_hit` が 0/35** だった。
理由は、部門別 Agent が**その部門のテーブルしか持たない**ので、
`sales_order.total_net_amount`（受注）と `trade_settlement.total_net_amount`（販促精算）が
**別の Agent に分かれていて、同名 measure に手が届かなかった**こと。

販促は実務では営業の中の機能なので営業に統合した。結果、営業 Agent が両方を同時に持ち、
**部門内で定義衝突が起きる**状態になった。統治前の測定で `trap_hit` が 2件に変わった。

## 統治 OFF / ON で何を出し入れするか

`06_genie/apply_instructions.py` が両方向に動かす。

| | 統治 OFF（統治前） | 統治 ON（統治後） |
|---|---|---|
| instructions | 会社の説明だけ（**「金額は日本円」とも書かない** — マーケが USD であることは統治で初めて教える） | 4つの衝突の正本を明示（約2,900字） |
| 例SQL | なし | **4件**（売上・受注と売上の差・マーケ投下額・USD/JPY の換算） |
| 横断マート | **外す** | 配る（営業/財務に2本、マーケに2本、横断に4本） |

### 横断マートを統治ONで初めて配る理由

`mart_revenue_definitions` / `mart_spend_definitions` / `mart_customer_360` /
`mart_brand_investment_return` は、**誰かが部門をまたいで意味を揃えたから存在する**もの。
統治前の状態に置いてしまうと、答えがマートのコメントとして先に漏れる
（実測で Genie が「mart_spend_definitions の説明でも『投下ではない』と明記されています」と
引用して正解していた）。これは測定として成立しないので外した。

## ハマりどころ

### `serialized_space` は `?include_serialized_space=true` が必要
`GET /api/2.0/genie/spaces/{id}` だけでは `serialized_space` キーが**存在しない**。
付けると返り、`etag` も一緒に来る。

### その etag を PATCH に付けると必ず弾かれる
`Space configuration has been modified since this export was taken`。
ビルダーが `serialized_space` を正規化するため。API のメッセージ自身が omit を案内している。

### 全ての id 付きリストが id 順でなければならない
`GenieSpaceBuilder.to_dict()` は `data_sources.tables` だけソートする。
API は `instructions.example_question_sqls` など**すべての id 付きリスト**の id 順を要求する
（`Invalid export proto: instructions.example_question_sqls must be sorted by id`）。
ビルダー側の漏れを `sort_id_lists()` で埋めた。

### Genie One は Genie Agent に自動ルーティングしないことがある
実機で「売上」と1語入れたところ、オントロジー検索 → テーブル検索で完結し、
**Agent は使われなかった**。
Workspace instructions が唯一の明示的な誘導手段で、**Genie Agent には効かない**
（docs 明記）。そのため Agent 側には `apply_instructions.py` で別途入れている。

### Genie One 自体の会話 API はワークスペースに無い
`/api/2.0/genie/conversations` 等は Not Found。自動で評価できるのは
Genie Agent（`/api/2.0/genie/spaces/{id}/start-conversation`）だけ。
Pages の効果は Genie One の手動確認で測る。

## 再現手順

```bash
python3 06_genie/create_agents.py             # 4本作る（統治前の状態・横断マート無し）
python3 06_genie/apply_instructions.py --off  # 統治OFF に戻す
python3 06_genie/apply_instructions.py        # 統治ON（正本＋例SQL＋横断マート）
```
