#!/usr/bin/env bash
set -euo pipefail

SUPPORT_DIR="$HOME/Library/Application Support/JobScoutDashboard"
DASHBOARD_DIR="$SUPPORT_DIR/dashboard"
DASHBOARD_HOST="127.0.0.1"
DASHBOARD_PORT="8787"
DASHBOARD_URL="http://127.0.0.1:8787/"
PUBLIC_DASHBOARD_URL="https://yadava5.github.io/job-automator/"
SERVER_OUT="$SUPPORT_DIR/server.out.log"
SERVER_ERR="$SUPPORT_DIR/server.err.log"
PYTHON="/usr/bin/python3"

url_ready() {
  CHECK_URL="$1" "$PYTHON" - <<'PY'
import os
import sys
import urllib.request

url = os.environ["CHECK_URL"]
try:
    with urllib.request.urlopen(url, timeout=1.5) as response:
        body = response.read(4096).decode("utf-8", errors="ignore")
except Exception:
    sys.exit(1)
sys.exit(0 if "Job Search Dashboard" in body else 1)
PY
}

server_ready() {
  url_ready "$DASHBOARD_URL"
}

if url_ready "$PUBLIC_DASHBOARD_URL"; then
  open -a "Google Chrome" "$PUBLIC_DASHBOARD_URL"
  exit 0
fi

if [[ ! -f "$DASHBOARD_DIR/index.html" ]]; then
  echo "Dashboard mirror is missing: $DASHBOARD_DIR/index.html" >&2
  exit 1
fi

if server_ready; then
  open -a "Google Chrome" "$DASHBOARD_URL"
  exit 0
fi

(
  sleep 0.5
  open -a "Google Chrome" "$DASHBOARD_URL"
) >/dev/null 2>&1 &

exec "$PYTHON" -m http.server "$DASHBOARD_PORT" \
  --bind "$DASHBOARD_HOST" \
  --directory "$DASHBOARD_DIR"
