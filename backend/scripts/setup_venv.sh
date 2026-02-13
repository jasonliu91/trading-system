#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -n "${PYTHON_BIN:-}" ]; then
  PYTHON_CANDIDATE="${PYTHON_BIN}"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON_CANDIDATE="python3.11"
elif command -v /opt/homebrew/bin/python3.10 >/dev/null 2>&1; then
  PYTHON_CANDIDATE="/opt/homebrew/bin/python3.10"
else
  PYTHON_CANDIDATE="python3"
fi

if [ ! -d ".venv" ]; then
  "${PYTHON_CANDIDATE}" -m venv .venv
fi

source .venv/bin/activate
python - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python >= 3.10 is required. Recreate .venv with PYTHON_BIN pointing to Python 3.10+.")
PY
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
fi

echo "Backend environment is ready."
