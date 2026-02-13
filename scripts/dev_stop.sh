#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.run"

stop_one() {
  local name="$1"
  local pid_file="${RUN_DIR}/${name}.pid"
  if [ ! -f "${pid_file}" ]; then
    echo "[${name}] not running (pid file missing)"
    return
  fi

  local pid
  pid="$(cat "${pid_file}")"
  if kill -0 "${pid}" >/dev/null 2>&1; then
    kill "${pid}" >/dev/null 2>&1 || true
    echo "[${name}] stopped (pid=${pid})"
  else
    echo "[${name}] stale pid file removed"
  fi
  rm -f "${pid_file}"
}

stop_one backend
stop_one frontend
stop_one agent

