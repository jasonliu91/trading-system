#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-/opt/trading-system}"
DRY_RUN="${DRY_RUN:-false}"
SYSTEMD_DIR="/etc/systemd/system"
NGINX_SITE_PATH="/etc/nginx/sites-available/trading-system.conf"
NGINX_LINK_PATH="/etc/nginx/sites-enabled/trading-system.conf"
RENDER_ROOT="${PROJECT_DIR}/deploy/.rendered"
SYSTEMD_RENDER_DIR="${RENDER_ROOT}/systemd"
NGINX_RENDER_FILE="${RENDER_ROOT}/nginx/trading-system.conf"

run_cmd() {
  if [ "${DRY_RUN}" = "true" ]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

echo "[0/4] Render deploy configs"
"${SCRIPT_DIR}/render_configs.sh"

echo "[1/4] Copy systemd service files"
run_cmd sudo cp "${SYSTEMD_RENDER_DIR}/trading-backend.service" "${SYSTEMD_DIR}/"
run_cmd sudo cp "${SYSTEMD_RENDER_DIR}/trading-agent.service" "${SYSTEMD_DIR}/"
run_cmd sudo cp "${SYSTEMD_RENDER_DIR}/trading-frontend.service" "${SYSTEMD_DIR}/"

echo "[2/4] Reload and enable services"
run_cmd sudo systemctl daemon-reload
run_cmd sudo systemctl enable trading-backend trading-agent trading-frontend
run_cmd sudo systemctl restart trading-backend trading-agent trading-frontend

echo "[3/4] Configure nginx site"
run_cmd sudo cp "${NGINX_RENDER_FILE}" "${NGINX_SITE_PATH}"
if [ ! -L "${NGINX_LINK_PATH}" ]; then
  run_cmd sudo ln -s "${NGINX_SITE_PATH}" "${NGINX_LINK_PATH}"
fi
run_cmd sudo nginx -t
run_cmd sudo systemctl reload nginx

echo "[4/4] Done"
echo "Use these commands to inspect:"
echo "  sudo systemctl status trading-backend trading-agent trading-frontend"
echo "  sudo journalctl -u trading-backend -n 100 --no-pager"
echo "  sudo journalctl -u trading-agent -n 100 --no-pager"
echo "  sudo journalctl -u trading-frontend -n 100 --no-pager"
