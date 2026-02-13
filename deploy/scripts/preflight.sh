#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/trading-system}"
BACKEND_DIR="${PROJECT_DIR}/backend"
FRONTEND_DIR="${PROJECT_DIR}/frontend"
ENV_FILE="${BACKEND_DIR}/.env"
NGINX_TEMPLATE="${PROJECT_DIR}/deploy/nginx/trading-system.conf"

fail() {
  echo "[FAIL] $1"
  exit 1
}

warn() {
  echo "[WARN] $1"
}

ok() {
  echo "[OK] $1"
}

echo "Running preflight checks for ${PROJECT_DIR}"

[ -d "${PROJECT_DIR}" ] || fail "Project directory not found: ${PROJECT_DIR}"
[ -d "${BACKEND_DIR}" ] || fail "Backend directory not found: ${BACKEND_DIR}"
[ -d "${FRONTEND_DIR}" ] || fail "Frontend directory not found: ${FRONTEND_DIR}"
[ -f "${ENV_FILE}" ] || fail "Missing backend .env file: ${ENV_FILE}"
[ -f "${NGINX_TEMPLATE}" ] || fail "Missing nginx template: ${NGINX_TEMPLATE}"

command -v python3 >/dev/null 2>&1 || fail "python3 is required"
command -v npm >/dev/null 2>&1 || fail "npm is required"

if [ "$(uname -s)" = "Linux" ]; then
  command -v systemctl >/dev/null 2>&1 || fail "systemctl is required on Linux target"
  command -v nginx >/dev/null 2>&1 || fail "nginx is required on Linux target"
else
  command -v systemctl >/dev/null 2>&1 || warn "systemctl not found (expected on non-Linux dev machine)"
  command -v nginx >/dev/null 2>&1 || warn "nginx not found (expected on non-Linux dev machine)"
fi

if grep -q "trade.your-domain.com" "${NGINX_TEMPLATE}"; then
  warn "nginx template still uses placeholder domain trade.your-domain.com"
else
  ok "nginx domain appears customized"
fi

if grep -q "^TELEGRAM_BOT_TOKEN=$" "${ENV_FILE}"; then
  warn "TELEGRAM_BOT_TOKEN is empty in ${ENV_FILE}"
fi

if grep -q "^TELEGRAM_CHAT_ID=$" "${ENV_FILE}"; then
  warn "TELEGRAM_CHAT_ID is empty in ${ENV_FILE}"
fi

if grep -q "^ANTHROPIC_API_KEY=$" "${ENV_FILE}" && grep -q "^OPENAI_API_KEY=$" "${ENV_FILE}"; then
  warn "Both ANTHROPIC_API_KEY and OPENAI_API_KEY are empty"
fi

if [ ! -x "${BACKEND_DIR}/.venv/bin/python" ]; then
  warn "backend virtualenv python not found (${BACKEND_DIR}/.venv/bin/python)"
else
  ok "backend virtualenv exists"
fi

if [ ! -f "${FRONTEND_DIR}/package.json" ]; then
  fail "frontend/package.json missing"
fi

ok "Preflight checks completed"
