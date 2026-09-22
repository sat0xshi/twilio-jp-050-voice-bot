#!/usr/bin/env bash
# Place one outbound call. Destination and caller ID come from .env.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -x .venv/bin/python ]]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python3
fi

exec "$PYTHON" -m app.outbound
