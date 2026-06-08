import unittest
from pathlib import Path


class StartupScriptTests(unittest.TestCase):
    def test_open_script_regenerates_when_report_is_newer_than_dashboard(self):
        script = Path("scripts/open_job_dashboard.sh").read_text(encoding="utf-8")

        self.assertIn('"$source" -nt "$sentinel"', script)
        self.assertIn("REGEN_SOURCES=(", script)
        self.assertIn("DASHBOARD_SENTINELS=(", script)
        self.assertIn('"$ROOT/job_scout/dashboard.py"', script)
        self.assertIn('"$ROOT/job_scout/generator.py"', script)
        self.assertIn('if [[ "$needs_regen" == true ]]; then', script)
        self.assertIn('for sentinel in "${DASHBOARD_SENTINELS[@]}"; do', script)
        self.assertIn('DASHBOARD_URL="http://127.0.0.1:8787/"', script)
        self.assertIn('ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"', script)
        self.assertIn('PYTHON="${JOB_AUTOMATOR_PYTHON:-python3}"', script)
        self.assertIn('PUBLIC_DASHBOARD_DIR="$ROOT/outputs/job-search/public-dashboard"', script)
        self.assertIn('PUBLIC_DASHBOARD="$PUBLIC_DASHBOARD_DIR/index.html"', script)
        self.assertIn('PUBLIC_DASHBOARD_DATA="$PUBLIC_DASHBOARD_DIR/data/latest.json"', script)
        self.assertIn('PUBLIC_DASHBOARD_MANIFEST="$PUBLIC_DASHBOARD_DIR/data/manifest.json"', script)
        self.assertIn('PUBLIC_DASHBOARD_URL="https://yadava5.github.io/job-automator/"', script)
        self.assertIn('PUBLISH_LOG="$HOME/Library/Application Support/JobScoutDashboard/pages-publish.log"', script)
        self.assertIn('MIRROR_DIR="$HOME/Library/Application Support/JobScoutDashboard/dashboard"', script)
        self.assertIn('ditto "$DASHBOARD_DIR" "$MIRROR_DIR"', script)
        self.assertIn('bash "$ROOT/scripts/publish_dashboard_pages.sh"', script)
        self.assertIn('--dashboard-dir "$PUBLIC_DASHBOARD_DIR"', script)
        self.assertIn("Public dashboard publish failed; opening local dashboard", script)
        self.assertIn('-m http.server "$DASHBOARD_PORT"', script)
        self.assertIn('--directory "$MIRROR_DIR"', script)
        self.assertIn('open -a "Google Chrome" "$DASHBOARD_URL"', script)

    def test_open_script_passes_run_date_and_uses_main_resume_default(self):
        script = Path("scripts/open_job_dashboard.sh").read_text(encoding="utf-8")

        self.assertIn('RUN_DATE="$(date +%F)"', script)
        self.assertIn('--run-date "$RUN_DATE"', script)
        self.assertIn('--application-pack-dir "$ROOT/outputs/job-search/application-packs/$RUN_DATE"', script)
        self.assertNotIn("Ayush Yadav Resume (Dec 2025).docx", script)

    def test_launch_agent_installer_uses_tracked_plist_and_opener(self):
        installer = Path("scripts/install_job_dashboard_launch_agent.sh").read_text(encoding="utf-8")
        plist = Path("scripts/com.ayush.job-dashboard.plist").read_text(encoding="utf-8")

        self.assertIn('PLIST_NAME="com.ayush.job-dashboard.plist"', installer)
        self.assertIn('SUPPORT_LAUNCHER="$SUPPORT_DIR/open_job_dashboard.sh"', installer)
        self.assertIn('cp "$ROOT/scripts/job_dashboard_support_launcher.sh" "$SUPPORT_LAUNCHER"', installer)
        self.assertIn('"$SRC" > "$DST"', installer)
        self.assertIn('chmod 755 "$SUPPORT_LAUNCHER"', installer)
        self.assertIn('chmod 755 "$DST"', installer)
        self.assertIn("__SUPPORT_LAUNCHER__", plist)
        self.assertIn("__LOG_DIR__/launch-agent.out.log", plist)
        self.assertIn("__LOG_DIR__/launch-agent.err.log", plist)
        self.assertIn("<string>/bin/bash</string>", plist)

    def test_support_launcher_serves_dashboard_mirror_without_documents_access(self):
        launcher = Path("scripts/job_dashboard_support_launcher.sh").read_text(encoding="utf-8")

        self.assertIn('DASHBOARD_DIR="$SUPPORT_DIR/dashboard"', launcher)
        self.assertIn('PUBLIC_DASHBOARD_URL="https://yadava5.github.io/job-automator/"', launcher)
        self.assertIn('if url_ready "$PUBLIC_DASHBOARD_URL"; then', launcher)
        self.assertIn('open -a "Google Chrome" "$PUBLIC_DASHBOARD_URL"', launcher)
        self.assertIn('if [[ ! -f "$DASHBOARD_DIR/index.html" ]]; then', launcher)
        self.assertIn('if server_ready; then', launcher)
        self.assertIn('sleep 0.5', launcher)
        self.assertIn('exec "$PYTHON" -m http.server "$DASHBOARD_PORT"', launcher)
        self.assertIn('-m http.server "$DASHBOARD_PORT"', launcher)
        self.assertIn('--directory "$DASHBOARD_DIR"', launcher)
        self.assertIn('open -a "Google Chrome" "$DASHBOARD_URL"', launcher)
        self.assertNotIn("New project 2", launcher)

    def test_tracked_startup_files_do_not_expose_personal_home_paths(self):
        for path in (
            Path("scripts/open_job_dashboard.sh"),
            Path("scripts/install_job_dashboard_launch_agent.sh"),
            Path("scripts/com.ayush.job-dashboard.plist"),
            Path("scripts/publish_dashboard_pages.sh"),
        ):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("/Users/private", text, path.as_posix())
            self.assertNotIn("Documents/Projects/job-automator", text, path.as_posix())


if __name__ == "__main__":
    unittest.main()
