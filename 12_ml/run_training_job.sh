#!/usr/bin/env bash
# 学習を Databricks の serverless ジョブで回す。
# ローカルに sklearn / numpy が無い（この Mac は /etc/hosts で pypi が塞がれている）し、
# MLflow の実験と UC レジストリは Databricks 側にあるので、向こうで動かすのが素直。
set -euo pipefail

P="${PROFILE:-fe-vm-serverless-rongzi-cpg-general}"
DEST="/Workspace/Users/rongzi.yan@databricks.com/brickshouse/ml"
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "1) 学習スクリプトをワークスペースへ"
databricks workspace mkdirs "$DEST" --profile "$P"
databricks workspace import "$DEST/train_conflict_ranker.py" \
  --file "$HERE/train_conflict_ranker.py" \
  --format RAW --language PYTHON --overwrite --profile "$P"

echo "2) serverless ジョブを作って実行"
RUN=$(databricks jobs submit --profile "$P" -o json --json "{
  \"run_name\": \"brickshouse-conflict-ranker\",
  \"tasks\": [{
    \"task_key\": \"train\",
    \"spark_python_task\": {\"python_file\": \"$DEST/train_conflict_ranker.py\"},
    \"environment_key\": \"default\"
  }],
  \"environments\": [{
    \"environment_key\": \"default\",
    \"spec\": {\"client\": \"3\", \"dependencies\": [\"scikit-learn==1.7.2\", \"pandas==2.2.3\", \"mlflow>=3\"]}
  }]
}" | python3 -I -c "import sys,json;print(json.load(sys.stdin)['run_id'])")
echo "   run_id=$RUN"

echo "3) 完了まで待つ"
for i in $(seq 1 90); do
  S=$(databricks jobs get-run "$RUN" --profile "$P" -o json \
      | python3 -I -c "import sys,json;d=json.load(sys.stdin);s=d.get('status') or {};print(s.get('state') or (d.get('state') or {}).get('life_cycle_state'))")
  case "$S" in
    TERMINATED|SUCCESS|SUCCEEDED|INTERNAL_ERROR|SKIPPED|FAILED)
      echo "   -> $S"; break;;
  esac
  sleep 20
done

echo "4) 出力"
databricks jobs get-run-output "$(databricks jobs get-run "$RUN" --profile "$P" -o json \
  | python3 -I -c "import sys,json;print(json.load(sys.stdin)['tasks'][0]['run_id'])")" \
  --profile "$P" -o json 2>/dev/null \
  | python3 -I -c "
import sys,json
d=json.load(sys.stdin)
print(d.get('logs') or json.dumps(d, ensure_ascii=False)[:2000])
" || echo "   出力の取得に失敗（UI で run_id=$RUN を見てください）"
