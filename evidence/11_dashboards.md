# AI/BI ダッシュボード3本

当初要件の「**ダッシュボードも ontology の snippet になる**」に対応するもの。
ダッシュボードが存在すると、その SQL が inferred ontology に取り込まれる。
つまり**見るためだけでなく、Genie に文脈を供給する資産**でもある。

| ダッシュボード | 主題 | KPI 3つ |
|---|---|---|
| **Brickshouse 営業（販促を含む）** | **受注と売上は違う** | 受注純額 / 純売上（正本） / 転換率 |
| **Brickshouse 財務** | **ここの数字が正本。どこで目減りするか** | 純売上 / リーケージ率 / 原価率 |
| **Brickshouse マーケティング** | **USD建てで、他部門と足せない** | 投下額(USD) / 消化率 / CPM(USD) |

いずれも公開済み。`/Workspace/Users/rongzi.yan@databricks.com/brickshouse/dashboards`

## デプロイ前に全 SQL を実機で検証した

`11_dashboards/validate.py` が、

1. 12データセットの SQL を実行して列と行が取れることを確かめる
2. データセットに宣言した measure 式を1つずつ実行する
3. **ウィジェットの `fieldName` が `query.fields` の名前と一致するか**を機械照合する
4. 生の列参照がデータセットの列に実在するかを確かめる

ウィジェットは SQL の出力列にそのまま結びつくので、**SQL が通らなければウィジェットは必ず壊れる**。
49ウィジェット・問題0件を確認してからデプロイした。

## 汚れを隠していない

注入したデータの汚れを、KPI として画面に出している。

- 営業: **未マップのチャネルコードの行数**（`スーパー` という想定外のコード値）
- マーケ: **通貨が記録されていない明細の数**（空を JPY と思って集計すると静かに間違う）

品質の問題を見えるようにするのが統治の画面だという判断。

## ハマりどころ

### テーブル名だけでは解決できなかった
docs は「ダッシュボード内の `FROM` はテーブル名のみ」としているが、
3本とも**複数スキーマにまたがる**（`sales_mart` + `xdept_mart` + `trade_mart` など）。
`--dataset-schema` は1つしか渡せないので、`schema.table` で書き、
**カタログだけを作成時のフラグから入れる**形にした。カタログ間の可搬性は保てる。

## 再現手順

```bash
python3 11_dashboards/sales.py && python3 11_dashboards/finance.py && python3 11_dashboards/marketing.py
python3 11_dashboards/validate.py 11_dashboards/*.json      # デプロイ前に必ず通す
# → databricks lakeview create ... （--dataset-catalog はフラグ必須・parent_path は JSON のみ）
```
