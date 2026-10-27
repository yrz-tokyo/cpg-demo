#!/usr/bin/env bash
# Lakebase にスキーマを適用する。
# 認証は OAuth トークンを毎回取り直す（1時間で切れるため使い捨て）。
set -euo pipefail

PROFILE="${PROFILE:-fe-vm-serverless-rongzi-cpg-general}"
INSTANCE="${INSTANCE:-brickshouse}"
DBNAME="${DBNAME:-databricks_postgres}"
USER_NAME="${USER_NAME:-rongzi.yan@databricks.com}"
HERE="$(cd "$(dirname "$0")" && pwd)"

HOST=$(databricks database get-database-instance "$INSTANCE" --profile "$PROFILE" -o json \
  | python3 -I -c "import json,sys; print(json.load(sys.stdin)['read_write_dns'])")
STATE=$(databricks database get-database-instance "$INSTANCE" --profile "$PROFILE" -o json \
  | python3 -I -c "import json,sys; print(json.load(sys.stdin)['state'])")
echo "instance=$INSTANCE state=$STATE host=$HOST"
[ "$STATE" = "AVAILABLE" ] || { echo "AVAILABLE ではありません。起動を待ってください。"; exit 1; }

TOKEN=$(databricks database generate-database-credential \
  --json "{\"instance_names\":[\"$INSTANCE\"],\"request_id\":\"$(uuidgen)\"}" \
  --profile "$PROFILE" -o json \
  | python3 -I -c "import json,sys; print(json.load(sys.stdin)['token'])")

export PGPASSWORD="$TOKEN" PGSSLMODE=require
psql -h "$HOST" -p 5432 -U "$USER_NAME" -d "$DBNAME" -v ON_ERROR_STOP=1 -f "$HERE/schema.sql"

echo "=== 適用結果 ==="
psql -h "$HOST" -p 5432 -U "$USER_NAME" -d "$DBNAME" -At -c "
SELECT table_schema || '.' || table_name
FROM information_schema.tables
WHERE table_schema IN ('semantics','app') ORDER BY 1"
