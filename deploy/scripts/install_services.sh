#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/trading-system}"
SYSTEMD_DIR="/etc/systemd/system"
NGINX_SITE_PATH="/etc/nginx/sites-available/trading-system.conf"
NGINX_LINK_PATH="/etc/nginx/sites-enabled/trading-system.conf"

echo "[1/4] Copy systemd service files"
sudo cp "${PROJECT_DIR}/deploy/systemd/trading-backend.service" "${SYSTEMD_DIR}/"
sudo cp "${PROJECT_DIR}/deploy/systemd/trading-agent.service" "${SYSTEMD_DIR}/"
sudo cp "${PROJECT_DIR}/deploy/systemd/trading-frontend.service" "${SYSTEMD_DIR}/"

echo "[2/4] Reload and enable services"
sudo systemctl daemon-reload
sudo systemctl enable trading-backend trading-agent trading-frontend
sudo systemctl restart trading-backend trading-agent trading-frontend

echo "[3/4] Configure nginx site"
sudo cp "${PROJECT_DIR}/deploy/nginx/trading-system.conf" "${NGINX_SITE_PATH}"
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

