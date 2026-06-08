import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


SCRIPT = Path("scripts/post_run_audit.py")
PYTHON = sys.executable


def write_resume_pdf(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path), pagesize=letter)
    text = pdf.beginText(36, 756)
    text.textLine("Ayush Yadav")
    text.textLine("Software Engineer")
    for index in range(120):
        text.textLine(f"Python React TypeScript SQL ML systems project achievement {index}")
    pdf.drawText(text)
    pdf.save()


def write_valid_run(root: Path, run_date: str = "2026-06-07"):
    output = root / "outputs" / "job-search"
    dashboard = output / "dashboard"
    public = output / "public-dashboard"
    pack = output / "application-packs" / run_date / "giga-software-engineer-new-grads"
    resume = pack / "Ayush-Yadav-Resume-{Giga}.pdf"
    write_resume_pdf(resume)
    (output / f"{run_date}.md").parent.mkdir(parents=True, exist_ok=True)
    (output / f"{run_date}.md").write_text("# Daily New Grad Job Scout\n", encoding="utf-8")
    (output / "latest.md").write_text("# Daily New Grad Job Scout\n", encoding="utf-8")
    for folder in (dashboard, public):
        (folder / "data" / "runs").mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text("<title>Job Search Dashboard</title>", encoding="utf-8")
    private_payload = {
        "run_id": "job-scout-dashboard-2026-06-07T120000",
        "run_date": run_date,
        "top_roles": [
            {
                "company": "Giga",
                "title": "Software Engineer",
                "resume_pdf": resume.resolve().as_uri(),
            }
        ],
        "easy_apply": [],
        "manual_review": [],
        "research": [],
        "stale": [],
    }
    public_payload = {
        "run_id": private_payload["run_id"],
        "run_date": run_date,
        "top_roles": [{"company": "Giga", "title": "Software Engineer", "primary_url": "https://example.com/apply"}],
        "easy_apply": [],
        "manual_review": [],
        "research": [],
        "stale": [],
    }
    manifest = {"latest_run_date": run_date, "runs": [{"run_date": run_date}]}
    for folder, payload in ((dashboard, private_payload), (public, public_payload)):
        (folder / "data" / "latest.json").write_text(json.dumps(payload), encoding="utf-8")
        (folder / "data" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (folder / "data" / "runs" / f"{run_date}.json").write_text(json.dumps(payload), encoding="utf-8")


class PostRunAuditTests(unittest.TestCase):
    def test_post_run_audit_writes_pass_summary_for_valid_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_valid_run(root)

            result = subprocess.run(
                [PYTHON, str(SCRIPT), "--root", str(root), "--run-date", "2026-06-07", "--skip-online"],
                check=False,
                text=True,
                capture_output=True,
            )
            audit_json = root / "outputs" / "job-search" / "run-audits" / "2026-06-07.json"
            audit = json.loads(audit_json.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["resume_pdf_count"], 1)
        self.assertEqual(audit["checks"]["public_privacy"]["status"], "pass")
        self.assertIn("Post-run audit passed", result.stdout)

    def test_post_run_audit_fails_when_public_dashboard_leaks_private_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_valid_run(root)
            public_latest = root / "outputs" / "job-search" / "public-dashboard" / "data" / "latest.json"
            public_latest.write_text('{"leak":"file:///Users/private/private.pdf"}', encoding="utf-8")

            result = subprocess.run(
                [PYTHON, str(SCRIPT), "--root", str(root), "--run-date", "2026-06-07", "--skip-online"],
                check=False,
                text=True,
                capture_output=True,
            )
            audit = json.loads(
                (root / "outputs" / "job-search" / "run-audits" / "2026-06-07.json").read_text(encoding="utf-8")
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(audit["passed"])
        self.assertEqual(audit["checks"]["public_privacy"]["status"], "fail")
        self.assertIn("Public dashboard contains private pattern", result.stderr)

    def test_online_run_retries_until_pages_serves_current_run_id(self):
        spec = importlib.util.spec_from_file_location("post_run_audit", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)

        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return json.dumps(self.payload).encode("utf-8")

        responses = [
            FakeResponse({"run_id": "old-run"}),
            FakeResponse({"run_id": "current-run"}),
        ]

        with (
            patch.object(module.urllib.request, "urlopen", side_effect=responses) as urlopen,
            patch.object(module.time, "sleep") as sleep,
        ):
            result = module.check_online_run(
                "https://example.com/job-automator/",
                "current-run",
                retries=2,
                retry_delay_seconds=0,
            )

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["online_run_id"], "current-run")
        self.assertEqual(urlopen.call_count, 2)
        self.assertEqual(sleep.call_count, 1)
        self.assertEqual([attempt["online_run_id"] for attempt in result["attempts"]], ["old-run", "current-run"])


if __name__ == "__main__":
    unittest.main()
