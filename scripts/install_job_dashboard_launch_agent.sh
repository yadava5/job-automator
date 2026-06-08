#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_NAME="com.ayush.job-dashboard.plist"
SRC="$ROOT/scripts/$PLIST_NAME"
DST="$HOME/Library/LaunchAgents/$PLIST_NAME"
SUPPORT_DIR="$HOME/Library/Application Support/JobScoutDashboard"
SUPPORT_LAUNCHER="$SUPPORT_DIR/open_job_dashboard.sh"
DASHBOARD_SRC="$ROOT/outputs/job-search/dashboard"
DASHBOARD_DST="$SUPPORT_DIR/dashboard"

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$SUPPORT_DIR"
cp "$ROOT/scripts/job_dashboard_support_launcher.sh" "$SUPPORT_LAUNCHER"
chmod 755 "$SUPPORT_LAUNCHER"
if [[ -d "$DASHBOARD_SRC" ]]; then
  mkdir -p "$DASHBOARD_DST"
  ditto "$DASHBOARD_SRC" "$DASHBOARD_DST"
fi
sed \
  -e "s#__SUPPORT_LAUNCHER__#$SUPPORT_LAUNCHER#g" \
  -e "s#__LOG_DIR__#$SUPPORT_DIR#g" \
  "$SRC" > "$DST"
chmod 755 "$DST"
launchctl unload "$DST" >/dev/null 2>&1 || true
launchctl load "$DST"
echo "Installed and loaded $DST"
