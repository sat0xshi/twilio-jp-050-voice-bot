#!/usr/bin/env bash
# Start the webhook server. Reads HOST and PORT from .env when that file exists.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -x .venv/bin/python ]]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python3
fi

mapfile -t bind < <("$PYTHON" - <<'PY'
import os
from dotenv import load_dotenv

load_dotenv()
print(os.getenv("HOST", "127.0.0.1"))
print(os.getenv("PORT", "8000"))
PY
)

exec "$PYTHON" -m uvicorn app.main:app --host "${bind[0]}" --port "${bind[1]}"
