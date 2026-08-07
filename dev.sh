#!/usr/bin/env bash
# Start LuxTJ backend locally (Linux / macOS)
# Usage: ./dev.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"
export PYTHONPATH="src"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install from https://docs.astral.sh/uv/ and reopen the terminal." >&2
  exit 1
fi

ENV_FILE="${ROOT}/.dev.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo ".dev.env not found. Copy .env.example to .dev.env and configure it." >&2
  exit 1
fi

# Load .dev.env into this process so uvicorn --reload child workers inherit vars.
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

PORT="${LTJBE_DEV_PORT:-9001}"
HOST="${LTJBE_DEV_HOST:-127.0.0.1}"

echo "Starting LuxTJ BE on http://${HOST}:${PORT}"
if [[ -n "${LTJBE_ADMIN_DEV_AUTH_ENABLED:-}" ]]; then
  echo "Admin dev auth enabled: ${LTJBE_ADMIN_DEV_AUTH_ENABLED}"
fi

exec uv run --env-file .dev.env uvicorn luxtj.bootstrap.api:server_factory \
  --factory \
  --host "${HOST}" \
  --port "${PORT}" \
  --reload \
  --reload-dir src
