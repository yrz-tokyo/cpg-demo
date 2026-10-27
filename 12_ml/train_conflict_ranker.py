#!/usr/bin/env python3
"""
衝突レビューの行列を並べ替えるモデルを学習する（Databricks の serverless で実行）。

このファイルはワークスペースにアップロードして Lakeflow Job（serverless）で動かす。
ローカルには sklearn が無く、MLflow の実験と UC レジストリは Databricks 側にあるため。

やること
  1. semantics_ops.conflict_feature（特徴量）と
     semantics_ops.conflict_label（人の判断）を読む
  2. 層化5分割の交差検証で PR-AUC と上位N件の適合率を出す
  3. **3つのベースラインと必ず比べる**:
       max_over_min 降順 / n_objects 降順 / ランダム
     勝てなければ「モデルは不要」が正しい結論になるので、負けたことも記録する
  4. MLflow に記録し、UC に登録する

モデルが主張できることは「保留した人の判断を再現できる」までで、
「人の知らない衝突を見つけた」ではない。詳細は 12_ml/LABELING_POLICY.md。
"""
from __future__ import annotations

import json
import os

import mlflow
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

CATALOG = os.getenv("BRICKSHOUSE_CATALOG", "rongzi_catalog_dev")
SCHEMA = "semantics_ops"
MODEL_NAME = f"{CATALOG}.{SCHEMA}.conflict_ranker"
EXPERIMENT = "/Users/rongzi.yan@databricks.com/brickshouse-conflict-ranker"

FEATURES = ["n_objects", "n_departments", "n_schemas", "log_max_over_min",
            "cross_layer", "n_currencies", "currency_mixed", "in_metric_view",
            "certified_count", "name_has_amount", "name_has_rate",
            "name_has_count", "name_has_usd", "comment_jaccard_avg"]


def load() -> pd.DataFrame:
    spark = __import__("pyspark.sql", fromlist=["SparkSession"]).SparkSession.builder.getOrCreate()
    f = spark.table(f"{CATALOG}.{SCHEMA}.conflict_feature").toPandas()
    y = spark.table(f"{CATALOG}.{SCHEMA}.conflict_label").toPandas()
    df = f.merge(y[["measure_name", "label", "rationale"]], on="measure_name", how="inner")
    df["log_max_over_min"] = np.log10(df["max_over_min"].clip(lower=1.0))
    # コメントが片方欠けていると類似度が計算できない。欠損は中央値で埋め、
    # 「欠損だった」こと自体も特徴量にする（欠損が偶然一致の目印になりうる）
    df["comment_missing"] = df["comment_jaccard_avg"].isna().astype(int)
    df["comment_jaccard_avg"] = df["comment_jaccard_avg"].fillna(
        df["comment_jaccard_avg"].median())
    return df


def baselines(df: pd.DataFrame, y: np.ndarray) -> dict:
    """モデルを使わずに並べたときの成績。これに勝てないならモデルは要らない。"""
    rng = np.random.default_rng(20261026)
    out = {}
    for name, score in (("baseline_max_over_min", df["log_max_over_min"].to_numpy()),
                        ("baseline_n_objects", df["n_objects"].to_numpy().astype(float)),
                        ("baseline_random", rng.random(len(df)))):
        out[f"{name}_pr_auc"] = float(average_precision_score(y, score))
        out[f"{name}_roc_auc"] = float(roc_auc_score(y, score))
        k = max(1, int(0.2 * len(df)))
        top = np.argsort(-score)[:k]
        out[f"{name}_precision_at_{k}"] = float(y[top].mean())
    return out


def main():
    mlflow.set_registry_uri("databricks-uc")
    mlflow.set_experiment(EXPERIMENT)
    df = load()
    cols = FEATURES + ["comment_missing"]
    X = df[cols].to_numpy(dtype=float)
    y = df["label"].to_numpy(dtype=int)
    k_top = max(1, int(0.2 * len(df)))
    print(f"学習データ {len(df)} グループ / 衝突あり {int(y.sum())} / なし {int((1-y).sum())}")

    candidates = {
        "logreg": Pipeline([("sc", StandardScaler()),
                            ("m", LogisticRegression(class_weight="balanced",
                                                     max_iter=2000, random_state=0))]),
        "gbdt": GradientBoostingClassifier(random_state=0, n_estimators=120,
                                           max_depth=2, learning_rate=0.08),
    }

    best = None
    with mlflow.start_run(run_name="conflict-ranker") as parent:
        mlflow.log_params({"n_samples": len(df), "n_positive": int(y.sum()),
                           "n_features": len(cols), "top_k": k_top,
                           "label_source": "builder-as-steward (synthetic data)",
                           "policy": "12_ml/LABELING_POLICY.md"})
        mlflow.log_metrics(baselines(df, y))

        for name, est in candidates.items():
            with mlflow.start_run(run_name=name, nested=True):
                skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
                oof = np.zeros(len(df))
                for tr, te in skf.split(X, y):
                    est.fit(X[tr], y[tr])
                    oof[te] = est.predict_proba(X[te])[:, 1]
                pr = float(average_precision_score(y, oof))
                roc = float(roc_auc_score(y, oof))
                top = np.argsort(-oof)[:k_top]
                p_at_k = float(y[top].mean())
                mlflow.log_metrics({"cv_pr_auc": pr, "cv_roc_auc": roc,
                                    f"cv_precision_at_{k_top}": p_at_k})
                print(f"  {name:8s} PR-AUC {pr:.3f}  ROC-AUC {roc:.3f}  "
                      f"上位{k_top}件の適合率 {p_at_k:.3f}")
                if best is None or pr > best[1]:
                    best = (name, pr, est, oof)

        name, pr, est, oof = best
        est.fit(X, y)
        mlflow.log_param("selected_model", name)
        sig = infer_signature(df[cols], est.predict_proba(X)[:, 1])
        info = mlflow.sklearn.log_model(est, name="model", signature=sig,
                                        input_example=df[cols].head(3),
                                        registered_model_name=MODEL_NAME)
        # 並べ替えの結果をそのまま証跡に残す（上位が本物かを目で見るため）
        rank = df.assign(score=oof).sort_values("score", ascending=False)
        rank_path = "/tmp/conflict_ranking.csv"
        rank[["measure_name", "score", "label", "n_objects", "n_departments",
              "max_over_min", "cross_layer", "n_currencies", "rationale"]].to_csv(
            rank_path, index=False)
        mlflow.log_artifact(rank_path)
        print(f"\n選んだモデル: {name} (PR-AUC {pr:.3f})")
        print(f"UC 登録: {MODEL_NAME}  version={info.registered_model_version}")
        print(f"run_id={parent.info.run_id}")
        print("\n上位10件（score 降順・label が実際の判断）")
        print(rank[["measure_name", "score", "label", "n_departments", "max_over_min"]]
              .head(10).to_string(index=False))
        meta = {"model_name": MODEL_NAME,
                "version": str(info.registered_model_version),
                "run_id": parent.info.run_id, "selected": name,
                "cv_pr_auc": pr, "n_samples": len(df), "n_positive": int(y.sum())}
        with open("/tmp/model_meta.json", "w") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=1)
        mlflow.log_artifact("/tmp/model_meta.json")
    return 0


if __name__ == "__main__":
    # SystemExit を投げると Databricks のジョブが RUN_EXECUTION_ERROR として扱う
    # （学習は成功していたのに失敗表示になった）。素直に return して終わる。
    main()
