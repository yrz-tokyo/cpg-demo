# Databricks App — 3画面

`09_app/`。React + Vite + TypeScript / FastAPI。
デザインは別途作った `venture-loop-demo` のトークンをそのまま使っている
（共通パレット1つ・アクセントは Databricks の lava のみ・16:9 投影前提）。

## 3画面はそれぞれ観客が違う

| | 画面 | 観客 | 中身 |
|---|---|---|---|
| ① | **現場の問い** | 顧客デモ | 6ペルソナ（3部門 × 部長/現場）を切り替え、その人の問いを押すと回答・生成SQL・**引用元**が出る |
| ② | **衝突を裁く** | データスチュワード | 検出結果と**各定義の実測値を並べて**比較し、業務用語と正本を人が決める → Lakebase → ML ラベル |
| ③ | **統治の効果** | FE Bar | 同じ49問の before / after。判定が変わった問いを上に出す |

## 設計で守ったこと

- **KPI は3つまで。** それぞれに単位・期間・基準・出所を添える
- **状態を色だけで区別しない。** 認定済み/未認定、正解/不正解/聞き返し は必ず文字でも書く
- **引用元を必ず出す。** AI の答えは、どこから来たかが見えないと業務では使えない。
  認定バッジ・部門タグ・そのオブジェクトのコメントまで出す
- **下段は動作する構成図。** `聞く人 → 問い → Genie Agent → 引用元 → 認定` の5ノードが
  応答が返ると実際に埋まる。ログではない
- **「聞き返し」を不正解と分けて数える。** 統治前に「どちらの売上ですか」と聞き返すのは
  正しい振る舞いであって誤答ではない

## 画面②がループの折り返し点

```
検出結果（Lakebase）→ 実測値を並べて表示 → 人が用語と正本を決める
                                              ↓
                      semantics.decision に書く（1トランザクション）
                                              ↓
                  却下なら rejected_pair も書く → 次回検出が再提案しない
                                              ↓
                  ml_training_label ビューが approve→1 / reject→0 を機械導出
                                              ↓
                          画面下の学習ラベル件数がその場で増える
```

**検出器(LLM)が付けた業務用語は人が画面で直せる。** 実測で `total_net_amount` に
「正味金額」と付けた（正しくは「売上」）。言葉を決めるのは人の仕事なので、直す口を用意した。

## 認可はサーバ側で判断する

画面のラベルを信じない。`CONFLICT_REVIEWERS` 環境変数に入っている人だけが
`/api/decide` を通せる（空ならデモ既定で全員可）。
画面前の人は Apps が入れる `x-forwarded-email` ヘッダで判定し、
ローカルでは CLI の自分になる。

## 実機で確認したこと

```
GET /api/me         → ユーザー・カタログ・Agent 4本・レビュー権限
GET /api/personas   → 6ペルソナ / 質問数 16,10,11,5,12,6 / 部門別 space_id
GET /api/conflicts  → Lakebase の衝突7件・候補23件・学習ラベル2件
GET /api/eval       → before/after の49問を1行ずつ並べたもの
```

## ハマりどころ

- **この Mac は `/etc/hosts` で pypi と npm registry が塞がれている。**
  依存は Databricks Apps 側で `requirements.txt` から解決させ、
  ローカル検証は別プロジェクトの venv と node_modules を借りた
- **Lakebase の接続を入れ子にしない。** 同じリクエストの中で2本開くと自分とデッドロックする。
  トークンは1時間で切れる使い捨てなのでプールを持たず毎回取り直す
- **`semantics.conflict` の `status` の許可値は** `detected / investigating / resolved / rejected`。
  `open` は無い（CHECK 制約で落ちる）
- **`audit_log` は `app` スキーマ**（`semantics` ではない）

## 起動

```bash
cd 09_app/frontend && npm run build
cd .. && DATABRICKS_CONFIG_PROFILE=<profile> python3 -m uvicorn app:app --port 8001
```
