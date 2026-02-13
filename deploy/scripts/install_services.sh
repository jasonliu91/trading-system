#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-/opt/trading-system}"
SYSTEMD_DIR="/etc/systemd/system"
NGINX_SITE_PATH="/etc/nginx/sites-available/trading-system.conf"
NGINX_LINK_PATH="/etc/nginx/sites-enabled/trading-system.conf"
RENDER_ROOT="${PROJECT_DIR}/deploy/.rendered"
SYSTEMD_RENDER_DIR="${RENDER_ROOT}/systemd"
NGINX_RENDER_FILE="${RENDER_ROOT}/nginx/trading-system.conf"

echo "[0/4] Render deploy configs"
"${SCRIPT_DIR}/render_configs.sh"

echo "[1/4] Copy systemd service files"
sudo cp "${SYSTEMD_RENDER_DIR}/trading-backend.service" "${SYSTEMD_DIR}/"
sudo cp "${SYSTEMD_RENDER_DIR}/trading-agent.service" "${SYSTEMD_DIR}/"
sudo cp "${SYSTEMD_RENDER_DIR}/trading-frontend.service" "${SYSTEMD_DIR}/"

echo "[2/4] Reload and enable services"
sudo systemctl daemon-reload
sudo systemctl enable trading-backend trading-agent trading-frontend
sudo systemctl restart trading-backend trading-agent trading-frontend

echo "[3/4] Configure nginx site"
sudo cp "${NGINX_RENDER_FILE}" "${NGINX_SITE_PATH}"
if [ ! -L "${NGINX_LINK_PATH}" ]; then
  sudo ln -s "${NGINX_SITE_PATH}" "${NGINX_LINK_PATH}"
fi
sudo nginx -t
sudo systemctl reload nginx

echo "[4/4] Done"
echo "Use these commands to inspect:"
echo "  sudo systemctl status trading-backend trading-agent trading-frontend"
echo "  sudo journalctl -u trading-backend -n 100 --no-pager"
echo "  sudo journalctl -u trading-agent -n 100 --no-pager"
echo "  sudo journalctl -u trading-frontend -n 100 --no-pager"
