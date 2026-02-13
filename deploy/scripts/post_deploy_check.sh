#!/usr/bin/env bash
set -euo pipefail

BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://127.0.0.1:8000/api/system/health}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:3000}"

echo "[1/4] Service status"
sudo systemctl --no-pager --full status trading-backend trading-agent trading-frontend | sed -n '1,120p'

echo "[2/4] Backend health"
curl -fsS "${BACKEND_HEALTH_URL}" && echo

echo "[3/4] Frontend root"
curl -fsSI "${FRONTEND_URL}" | sed -n '1,20p'

echo "[4/4] Recent logs"
sudo journalctl -u trading-backend -n 30 --no-pager
sudo journalctl -u trading-agent -n 30 --no-pager
sudo journalctl -u trading-frontend -n 30 --no-pager

echo "Post deploy checks completed."

