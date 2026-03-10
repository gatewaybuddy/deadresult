#!/usr/bin/env bash
# Deploy DeadResult from local machine (same as what GitHub Actions does).
# Usage: DB_PASSWORD=yourpassword ./deploy-local.sh [dev|prod]
set -euo pipefail

ENV="${1:-dev}"

if [ -z "${DB_PASSWORD:-}" ]; then
  echo "Error: DB_PASSWORD environment variable is required"
  echo "Usage: DB_PASSWORD=yourpassword ./deploy-local.sh [dev|prod]"
  exit 1
fi

echo "==> Building (env: $ENV)..."
sam build --template-file infra/template.yaml

echo "==> Deploying..."
sam deploy \
  --config-env "$ENV" \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  --parameter-overrides "Stage=$ENV DBPassword=$DB_PASSWORD"

echo "==> Done. Stack: deadresult-$ENV"
