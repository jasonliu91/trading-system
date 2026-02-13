#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.run"
mkdir -p "${RUN_DIR}"

start_backend() {
  if [ -f "${RUN_DIR}/backend.pid" ] && kill -0 "$(cat "${RUN_DIR}/backend.pid")" >/dev/null 2>&1; then
    echo "[backend] already running (pid=$(cat "${RUN_DIR}/backend.pid"))"
    return
  fi
  (
    cd "${ROOT_DIR}/backend"
    source .venv/bin/activate
    nohup uvicorn src.api.main:app --host 127.0.0.1 --port 8000 >"${RUN_DIR}/backend.log" 2>&1 &
    echo $! > "${RUN_DIR}/backend.pid"
  )
  echo "[backend] started (pid=$(cat "${RUN_DIR}/backend.pid"))"
}

start_frontend() {
  if [ -f "${RUN_DIR}/frontend.pid" ] && kill -0 "$(cat "${RUN_DIR}/frontend.pid")" >/dev/null 2>&1; then
    echo "[frontend] already running (pid=$(cat "${RUN_DIR}/frontend.pid"))"
    return
  fi
  (
    cd "${ROOT_DIR}/frontend"
    nohup npm run dev >"${RUN_DIR}/frontend.log" 2>&1 &
    echo $! > "${RUN_DIR}/frontend.pid"
  )
  echo "[frontend] started (pid=$(cat "${RUN_DIR}/frontend.pid"))"
}

start_agent() {
  if [ "${START_AGENT:-false}" != "true" ]; then
    echo "[agent] skipped (set START_AGENT=true to enable)"
    return
  fi

  if [ -f "${RUN_DIR}/agent.pid" ] && kill -0 "$(cat "${RUN_DIR}/agent.pid")" >/dev/null 2>&1; then
    echo "[agent] already running (pid=$(cat "${RUN_DIR}/agent.pid"))"
    return
  fi

  if [ ! -f "${ROOT_DIR}/backend/.env" ]; then
    echo "[agent] skipped (missing backend/.env)"
    return
  fi

  if grep -q "^TELEGRAM_BOT_TOKEN=$" "${ROOT_DIR}/backend/.env"; then
    echo "[agent] skipped (TELEGRAM_BOT_TOKEN is empty)"
    return
  fi

  (
    cd "${ROOT_DIR}/backend"
    source .venv/bin/activate
    nohup python -m src.agent.main >"${RUN_DIR}/agent.log" 2>&1 &
    echo $! > "${RUN_DIR}/agent.pid"
  )
  echo "[agent] started (pid=$(cat "${RUN_DIR}/agent.pid"))"
}

start_backend
start_frontend
start_agent

echo "Logs:"
echo "  ${RUN_DIR}/backend.log"
echo "  ${RUN_DIR}/frontend.log"
echo "  ${RUN_DIR}/agent.log"

