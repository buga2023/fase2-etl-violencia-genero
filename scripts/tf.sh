#!/usr/bin/env bash
# Roda o terraform lendo o token do .env (assim ele nunca fica em arquivo versionado).
# Uso: ./scripts/tf.sh init | plan | apply | output
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
export TF_VAR_aiven_api_token="$AIVEN_API_TOKEN"
terraform -chdir=terraform "$@"
