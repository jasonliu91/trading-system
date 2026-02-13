#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-/opt/trading-system}"
DRY_RUN="${DRY_RUN:-false}"

SKIP_BACKEND_SETUP="${SKIP_BACKEND_SETUP:-false}"
SKIP_FRONTEND_BUILD="${SKIP_FRONTEND_BUILD:-false}"

echo "[full-deploy] project=${PROJECT_DIR}"

cd "${PROJECT_DIR}"

echo "[1/5] preflight"
"${SCRIPT_DIR}/preflight.sh"

if [ "${SKIP_BACKEND_SETUP}" != "true" ]; then
  echo "[2/5] backend setup"
  cd "${PROJECT_DIR}/backend"
  ./scripts/setup_venv.sh
else
  echo "[2/5] backend setup skipped"
fi

if [ "${SKIP_FRONTEND_BUILD}" != "true" ]; then
  echo "[3/5] frontend build"
  cd "${PROJECT_DIR}/frontend"
  npm install
  npm run build
else
  echo "[3/5] frontend build skipped"
fi

echo "[4/5] install services"
DRY_RUN="${DRY_RUN}" "${SCRIPT_DIR}/install_services.sh"

echo "[5/5] post deploy check"
if [ "${DRY_RUN}" = "true" ]; then
  echo "[dry-run] skip post deploy check"
else
  "${SCRIPT_DIR}/post_deploy_check.sh"
fi

echo "[full-deploy] completed"
