import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("scripts/publish_dashboard_pages.sh")


class PagesPublishScriptTests(unittest.TestCase):
    def test_publish_script_uses_isolated_pages_worktree_and_privacy_gate(self):
        script = SCRIPT.read_text(encoding="utf-8")

        self.assertIn('PUBLIC_DASHBOARD_DIR="$ROOT/outputs/job-search/public-dashboard"', script)
        self.assertIn('PAGES_WORKTREE="$ROOT/tmp/job-automator-pages"', script)
        self.assertIn('BRANCH="gh-pages"', script)
        self.assertIn('PUBLIC_URL="https://yadava5.github.io/job-automator/"', script)
        self.assertIn("FORBIDDEN_PATTERNS=(", script)
        self.assertIn("'file://'", script)
        self.assertIn("'/Users/'", script)
        self.assertIn("'evidence-ledger'", script)
        self.assertIn("'validation-report'", script)
        self.assertIn("'application-packs'", script)
        self.assertIn("'\\.docx'", script)
        self.assertIn("'\\.pdf'", script)
        self.assertIn('git -C "$ROOT" worktree add', script)
        self.assertIn("Refusing to publish from wrong worktree branch", script)
        self.assertIn('branch --show-current', script)
        self.assertIn('rsync -a --delete --exclude', script)
        self.assertIn('git -C "$PAGES_WORKTREE" push "$REMOTE" "$BRANCH"', script)
        self.assertIn("No public dashboard file changes; pushing existing branch state.", script)
        self.assertIn('if [[ "$DRY_RUN" == true ]]; then', script)

    def test_verify_only_accepts_sanitized_public_dashboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            public_dir = Path(tmp)
            data_dir = public_dir / "data"
            data_dir.mkdir()
            (public_dir / "index.html").write_text("<title>Job Search Dashboard</title>", encoding="utf-8")
            (data_dir / "latest.json").write_text('{"top_roles":[]}', encoding="utf-8")
            (data_dir / "manifest.json").write_text('{"runs":[]}', encoding="utf-8")

            result = subprocess.run(
                ["bash", str(SCRIPT), "--dashboard-dir", str(public_dir), "--verify-only"],
                check=False,
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Public dashboard privacy gate passed", result.stdout)

    def test_verify_only_ignores_git_worktree_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            public_dir = Path(tmp)
            data_dir = public_dir / "data"
            data_dir.mkdir()
            (public_dir / ".git").write_text("gitdir: /Users/private/.git/worktrees/pages\n", encoding="utf-8")
            (public_dir / "index.html").write_text("<title>Job Search Dashboard</title>", encoding="utf-8")
            (data_dir / "latest.json").write_text('{"top_roles":[]}', encoding="utf-8")
            (data_dir / "manifest.json").write_text('{"runs":[]}', encoding="utf-8")

            result = subprocess.run(
                ["bash", str(SCRIPT), "--dashboard-dir", str(public_dir), "--verify-only"],
                check=False,
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Public dashboard privacy gate passed", result.stdout)

    def test_verify_only_rejects_private_public_dashboard_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            public_dir = Path(tmp)
            data_dir = public_dir / "data"
            data_dir.mkdir()
            (public_dir / "index.html").write_text("<title>Job Search Dashboard</title>", encoding="utf-8")
            (data_dir / "latest.json").write_text(
                '{"resume_pdf":"file:///Users/private/application-packs/Ayush-Yadav-Resume-{Giga}.pdf"}',
                encoding="utf-8",
            )
            (data_dir / "manifest.json").write_text('{"runs":[]}', encoding="utf-8")

            result = subprocess.run(
                ["bash", str(SCRIPT), "--dashboard-dir", str(public_dir), "--verify-only"],
                check=False,
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refusing to publish private dashboard payload", result.stderr)
        self.assertIn("file://", result.stderr)


if __name__ == "__main__":
    unittest.main()
