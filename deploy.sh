#!/usr/bin/env bash
set -euo pipefail

STACK_NAME="${STACK_NAME:-deadresult-dev}"
STAGE="${STAGE:-dev}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
SAM_CONFIG="samconfig.toml"

echo "=== DeadResult Deploy ==="
echo "Stack: $STACK_NAME | Stage: $STAGE | Region: $REGION"

# -----------------------------------------------
# 1. Build
# -----------------------------------------------
echo ""
echo "--- Building SAM package ---"
sam build --use-container

# -----------------------------------------------
# 2. Deploy
# -----------------------------------------------
echo ""
if [ -f "$SAM_CONFIG" ]; then
    echo "--- Deploying (using saved config) ---"
    sam deploy --no-confirm-changeset
else
    echo "--- Deploying (first time — guided) ---"
    sam deploy --guided \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --capabilities CAPABILITY_IAM \
        --parameter-overrides "Stage=$STAGE"
fi

# -----------------------------------------------
# 3. Retrieve outputs for migration
# -----------------------------------------------
echo ""
echo "--- Retrieving stack outputs ---"

DB_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='DatabaseEndpoint'].OutputValue" \
    --output text)

API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
    --output text)

echo "Database endpoint: $DB_ENDPOINT"
echo "API URL:           $API_URL"

# -----------------------------------------------
# 4. Run Alembic migrations
# -----------------------------------------------
echo ""
echo "--- Running database migrations ---"

if [ -z "${DB_PASSWORD:-}" ]; then
    echo "ERROR: Set DB_PASSWORD env var to run migrations."
    echo "  export DB_PASSWORD=<your-rds-password>"
    echo "  Then re-run: $0"
    exit 1
fi

# pgvector extension must be enabled by a superuser or via RDS parameter group.
# The migration script includes CREATE EXTENSION IF NOT EXISTS vector,
# which works if the rds_superuser role is granted (default for master user).

export DEADRESULT_DATABASE_URL_SYNC="postgresql://deadresult:${DB_PASSWORD}@${DB_ENDPOINT}:5432/deadresult"

echo "Running alembic upgrade head..."
alembic upgrade head

echo ""
echo "--- Migration complete ---"

# -----------------------------------------------
# 5. Verify
# -----------------------------------------------
echo ""
echo "--- Verifying deployment ---"
HEALTH=$(curl -s --max-time 10 "${API_URL}/health" || echo '{"error": "unreachable"}')
echo "Health check: $HEALTH"

echo ""
echo "=== Deploy complete ==="
echo "API:  $API_URL"
echo "Docs: ${API_URL}/docs"
