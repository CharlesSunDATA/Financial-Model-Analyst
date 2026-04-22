#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "Starting Streamlit with: $(pwd)/app.py" >&2
exec python3 -m streamlit run app.py "$@"

