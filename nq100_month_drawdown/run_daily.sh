#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
LOG_DIR="$PWD/logs"
mkdir -p "$LOG_DIR"
if [[ ! -x .venv/bin/python ]]; then
  echo "請先：python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi
exec >>"$LOG_DIR/daily.log" 2>&1
echo "===== $(date -u '+%Y-%m-%dT%H:%M:%SZ') ====="
exec .venv/bin/python main.py
