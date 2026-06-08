#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="$ROOT/outputs/job-search/latest.md"
DASHBOARD="$ROOT/outputs/job-search/dashboard/index.html"
DASHBOARD_DIR="$ROOT/outputs/job-search/dashboard"
PUBLIC_DASHBOARD_DIR="$ROOT/outputs/job-search/public-dashboard"
PUBLIC_DASHBOARD="$PUBLIC_DASHBOARD_DIR/index.html"
PUBLIC_DASHBOARD_DATA="$PUBLIC_DASHBOARD_DIR/data/latest.json"
PUBLIC_DASHBOARD_MANIFEST="$PUBLIC_DASHBOARD_DIR/data/manifest.json"
MIRROR_DIR="$HOME/Library/Application Support/JobScoutDashboard/dashboard"
DASHBOARD_HOST="127.0.0.1"
DASHBOARD_PORT="8787"
DASHBOARD_URL="http://127.0.0.1:8787/"
PUBLIC_DASHBOARD_URL="https://yadava5.github.io/job-automator/"
PUBLISH_LOG="$HOME/Library/Application Support/JobScoutDashboard/pages-publish.log"
SERVER_OUT="$HOME/Library/Application Support/JobScoutDashboard/server.out.log"
SERVER_ERR="$HOME/Library/Application Support/JobScoutDashboard/server.err.log"
PYTHON="${JOB_AUTOMATOR_PYTHON:-python3}"
RUN_DATE="$(date +%F)"
REGEN_SOURCES=(
  "$REPORT"
  "$ROOT/scripts/generate_job_dashboard.py"
  "$ROOT/job_scout/dashboard.py"
  "$ROOT/job_scout/generator.py"
  "$ROOT/job_scout/resume_pipeline.py"
  "$ROOT/job_scout/main_resume.py"
)
DASHBOARD_SENTINELS=(
  "$DASHBOARD"
  "$PUBLIC_DASHBOARD"
  "$PUBLIC_DASHBOARD_DATA"
  "$PUBLIC_DASHBOARD_MANIFEST"
)

needs_regen=false
for sentinel in "${DASHBOARD_SENTINELS[@]}"; do
  if [[ ! -f "$sentinel" ]]; then
    needs_regen=true
    break
  fi
done

if [[ "$needs_regen" == false ]]; then
  for source in "${REGEN_SOURCES[@]}"; do
    if [[ -f "$source" ]]; then
      for sentinel in "${DASHBOARD_SENTINELS[@]}"; do
        if [[ "$source" -nt "$sentinel" ]]; then
          needs_regen=true
          break 2
        fi
      done
    fi
  done
fi

if [[ "$needs_regen" == true ]]; then
  "$PYTHON" "$ROOT/scripts/generate_job_dashboard.py" \
    --report "$REPORT" \
    --dashboard-dir "$DASHBOARD_DIR" \
    --application-pack-dir "$ROOT/outputs/job-search/application-packs/$RUN_DATE" \
    --run-date "$RUN_DATE" \
    --limit 30
fi

mkdir -p "$MIRROR_DIR"
ditto "$DASHBOARD_DIR" "$MIRROR_DIR"

if [[ -f "$PUBLIC_DASHBOARD" ]]; then
  mkdir -p "$(dirname "$PUBLISH_LOG")"
  if bash "$ROOT/scripts/publish_dashboard_pages.sh" \
      --dashboard-dir "$PUBLIC_DASHBOARD_DIR" \
      >>"$PUBLISH_LOG" 2>&1; then
    echo "Published public dashboard: $PUBLIC_DASHBOARD_URL"
  else
    echo "Public dashboard publish failed; opening local dashboard. See $PUBLISH_LOG" >&2
  fi
fi

server_ready() {
  DASHBOARD_URL="$DASHBOARD_URL" "$PYTHON" - <<'PY'
import os
import sys
import urllib.request

url = os.environ["DASHBOARD_URL"]
try:
    with urllib.request.urlopen(url, timeout=1.5) as response:
        body = response.read(4096).decode("utf-8", errors="ignore")
except Exception:
    sys.exit(1)
sys.exit(0 if "Job Search Dashboard" in body else 1)
PY
}

if ! server_ready; then
  mkdir -p "$(dirname "$SERVER_OUT")"
  nohup "$PYTHON" -m http.server "$DASHBOARD_PORT" \
    --bind "$DASHBOARD_HOST" \
    --directory "$MIRROR_DIR" \
    >"$SERVER_OUT" 2>"$SERVER_ERR" &

  for _ in {1..25}; do
    if server_ready; then
      break
    fi
    sleep 0.2
  done
fi

if ! server_ready; then
  echo "Dashboard server did not start at $DASHBOARD_URL" >&2
  echo "See $SERVER_ERR" >&2
  exit 1
fi

open -a "Google Chrome" "$DASHBOARD_URL"
