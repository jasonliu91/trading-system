#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"

DEPLOY_USER="${DEPLOY_USER:-ubuntu}"
PUBLIC_DOMAIN="${PUBLIC_DOMAIN:-trade.your-domain.com}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
FRONTEND_API_BASE_URL="${FRONTEND_API_BASE_URL:-https://${PUBLIC_DOMAIN}}"

RENDER_ROOT="${PROJECT_DIR}/deploy/.rendered"
SYSTEMD_RENDER_DIR="${RENDER_ROOT}/systemd"
NGINX_RENDER_DIR="${RENDER_ROOT}/nginx"

mkdir -p "${SYSTEMD_RENDER_DIR}" "${NGINX_RENDER_DIR}"

render_file() {
  local src="$1"
  local dst="$2"
  sed \
    -e "s|User=ubuntu|User=${DEPLOY_USER}|g" \
    -e "s|/opt/trading-system|${PROJECT_DIR}|g" \
    -e "s|trade.your-domain.com|${PUBLIC_DOMAIN}|g" \
    -e "s|http://127.0.0.1:8000|http://${BACKEND_HOST}:${BACKEND_PORT}|g" \
    -e "s|http://127.0.0.1:3000|http://${BACKEND_HOST}:${FRONTEND_PORT}|g" \
    -e "s|Environment=NEXT_PUBLIC_API_BASE_URL=.*|Environment=NEXT_PUBLIC_API_BASE_URL=${FRONTEND_API_BASE_URL}|g" \
    "$src" > "$dst"
}

render_file "${PROJECT_DIR}/deploy/systemd/trading-backend.service" "${SYSTEMD_RENDER_DIR}/trading-backend.service"
render_file "${PROJECT_DIR}/deploy/systemd/trading-agent.service" "${SYSTEMD_RENDER_DIR}/trading-agent.service"
render_file "${PROJECT_DIR}/deploy/systemd/trading-frontend.service" "${SYSTEMD_RENDER_DIR}/trading-frontend.service"
render_file "${PROJECT_DIR}/deploy/nginx/trading-system.conf" "${NGINX_RENDER_DIR}/trading-system.conf"

echo "Rendered deploy configs:"
echo "  ${SYSTEMD_RENDER_DIR}/trading-backend.service"
echo "  ${SYSTEMD_RENDER_DIR}/trading-agent.service"
echo "  ${SYSTEMD_RENDER_DIR}/trading-frontend.service"
echo "  ${NGINX_RENDER_DIR}/trading-system.conf"

