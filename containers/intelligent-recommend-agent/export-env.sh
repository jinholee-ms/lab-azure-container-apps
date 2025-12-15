#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./export-env.sh <RESOURCE_GROUP> <CONTAINER_APP_NAME> [<CONTAINER_NAME>]
#
# 예:
#   ./export-env.sh rg-client-container-apps-community-001 ca-intel-rec-agent ca-intel-rec-agent

RESOURCE_GROUP="$1"
APP_NAME="$2"
CONTAINER_NAME="${3:-}"   # 옵션: 컨테이너 이름

ENV_FILE=".env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ $ENV_FILE file not found!"
  exit 1
fi

echo "📌 Loading env vars from $ENV_FILE..."

ENV_ARGS=()

# .env -> KEY=VALUE 들로 변환
while IFS='=' read -r key value; do
  # 주석 / 빈 줄 스킵
  [[ -z "$key" ]] && continue
  [[ "$key" =~ ^[[:space:]]*# ]] && continue

  key="$(echo "$key" | xargs)"
  value="$(echo "$value" | xargs)"

  [[ -z "$key" ]] && continue

  ENV_ARGS+=("$key=$value")
done < "$ENV_FILE"

if [[ ${#ENV_ARGS[@]} -eq 0 ]]; then
  echo "⚠️  No env vars parsed from $ENV_FILE. Abort."
  exit 1
fi

echo "📌 Env vars to apply:"
for kv in "${ENV_ARGS[@]}"; do
  echo "  - $kv"
done

# 컨테이너 이름 옵션 설정
CONTAINER_ARGS=()
if [[ -n "$CONTAINER_NAME" ]]; then
  CONTAINER_ARGS=(--container-name "$CONTAINER_NAME")
fi

echo "📌 Applying env to Container App '$APP_NAME' in RG '$RESOURCE_GROUP'..."
az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  "${CONTAINER_ARGS[@]}" \
  --set-env-vars "${ENV_ARGS[@]}"

echo "✅ Done"