# Brickshouse Food and Beverage — CPG 部門横断 Genie One デモ

架空の CPG 企業を題材に、**部門ごとに「売上」の定義が割れている状態で Genie One を
全社に入れると何が起きるか**を実機で測り、Unity Catalog の統治で直すまでを作ったもの。
データはすべて合成。

**最初に読むのは [`00_SUBMISSION.md`](00_SUBMISSION.md)**（結論・6コンポーネント対応・再現手順）。

| 読みたいもの | ファイル |
|---|---|
| 結論と測定結果 | [`00_SUBMISSION.md`](00_SUBMISSION.md) |
| 全工程とハマりどころ27件 | [`BUILD_LOG.md`](BUILD_LOG.md) |
| 顧客デモの進め方 | [`DEMO_PLAN_V2.md`](DEMO_PLAN_V2.md) |
| 証跡（評価・ML・App・ばらつき） | [`evidence/`](evidence/) |

`PLAN.md` / `STATUS.md` / `DEMO_DESIGN.md` / `SCHEMA_DESIGN.md` は着手前のメモで、
最終成果と食い違う箇所がある（各ファイル冒頭に注記あり）。

## 生成データは入っていない

`02_data/raw` `clean` `landing`（58MB）は除外している。`SEED=20261025` で決定的に
再生成できる。

```bash
python3 02_data/generate.py            # 206,028行
python3 02_data/generate.py --no-dirt  # 汚れ無しの比較用
```
