import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from job_scout.config import (
    APPLICATION_PACKS_DIR,
    DASHBOARD_DIR,
    EXTERNAL_NEW_RESUME_PDF,
    JOB_AUTOMATOR_PAGES_WORKTREE,
    LATEST_REPORT,
    MAIN_RESUME_DOCX,
    NEW_RESUME_PDF,
    ORIGINAL_RESUME_DOCX,
    PUBLIC_DASHBOARD_URL,
)
from job_scout.generator import generate_from_report
from scripts.generate_job_dashboard import (
    build_parser,
    default_application_pack_dir,
    default_source_resume,
    resolve_dashboard_dirs,
    resolve_source_resume,
)


SOURCE_RESUME = ORIGINAL_RESUME_DOCX


class GeneratorDefaultPathTests(unittest.TestCase):
    def test_generator_default_source_resume_points_to_new_icloud_pdf(self):
        self.assertEqual(default_source_resume(), NEW_RESUME_PDF)
        self.assertEqual(NEW_RESUME_PDF.name, "Ayush-Yadav-Resume.pdf")
        self.assertIn("resume/source/current", NEW_RESUME_PDF.as_posix())
        self.assertTrue(EXTERNAL_NEW_RESUME_PDF is None or EXTERNAL_NEW_RESUME_PDF.exists())

    def test_cli_parser_defaults_use_new_resume_and_private_dashboard(self):
        args = build_parser().parse_args([])

        self.assertEqual(Path(args.source_resume), NEW_RESUME_PDF)
        self.assertEqual(Path(args.report), LATEST_REPORT)
        self.assertEqual(Path(args.dashboard_dir), DASHBOARD_DIR)
        self.assertEqual(Path(args.public_dashboard_dir), DASHBOARD_DIR.parent / "public-dashboard")
        self.assertRegex(args.run_date, r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(args.application_pack_dir, "")
        self.assertFalse(args.skip_public_dashboard)

    def test_cli_generation_accepts_public_dashboard_paths(self):
        args = build_parser().parse_args([
            "--public-dashboard-dir",
            "/tmp/job-scout-public-dashboard",
        ])

        self.assertEqual(Path(args.public_dashboard_dir), Path("/tmp/job-scout-public-dashboard"))
        self.assertFalse(args.skip_public_dashboard)

    def test_public_dashboard_dir_must_not_equal_private_dashboard_dir(self):
        parser = build_parser()
        args = parser.parse_args([
            "--dashboard-dir",
            "/tmp/job-scout-dashboard",
            "--public-dashboard-dir",
            "/tmp/job-scout-dashboard",
        ])

        with self.assertRaisesRegex(ValueError, "public dashboard dir must differ"):
            resolve_dashboard_dirs(args)

    def test_public_dashboard_dir_can_match_private_when_public_output_skipped(self):
        parser = build_parser()
        args = parser.parse_args([
            "--dashboard-dir",
            "/tmp/job-scout-dashboard",
            "--public-dashboard-dir",
            "/tmp/job-scout-dashboard",
            "--skip-public-dashboard",
        ])

        private_dir, public_dir = resolve_dashboard_dirs(args)

        self.assertEqual(private_dir, Path("/tmp/job-scout-dashboard"))
        self.assertEqual(public_dir, Path("/tmp/job-scout-dashboard"))

    def test_pages_config_uses_isolated_worktree_and_stable_url(self):
        self.assertEqual(JOB_AUTOMATOR_PAGES_WORKTREE.name, "job-automator-pages")
        self.assertIn("/tmp/", JOB_AUTOMATOR_PAGES_WORKTREE.as_posix())
        self.assertEqual(PUBLIC_DASHBOARD_URL, "https://yadava5.github.io/job-automator/")

    def test_default_application_pack_dir_uses_run_date(self):
        self.assertEqual(default_application_pack_dir("2026-06-04"), APPLICATION_PACKS_DIR / "2026-06-04")

    def test_missing_new_default_resume_does_not_fall_back_to_original_resume(self):
        with patch.object(Path, "exists", return_value=False):
            resolved = resolve_source_resume(NEW_RESUME_PDF)

        self.assertEqual(resolved, NEW_RESUME_PDF)

    def test_arbitrary_missing_source_resume_does_not_fall_back(self):
        missing_source = Path("/tmp/missing-user-source.docx")

        with patch.object(Path, "exists", return_value=False):
            resolved = resolve_source_resume(missing_source)

        self.assertEqual(resolved, missing_source)


class GeneratorTests(unittest.TestCase):
    @unittest.skipUnless(MAIN_RESUME_DOCX.exists(), "requires private 2026 main resume DOCX")
    def test_generate_from_report_records_main_resume_source_and_pack_url(self):
        markdown = """
## Apply Today Top 10

| # | Company | Title | Location | Fit | Salary | Status | Link | Tailoring |
|---:|---|---|---|---:|---|---|---|---|
| 1 | Instabase | Full-stack Software Engineer (New Grad) | San Francisco, CA | 95 | $140,000-$145,455 | apply_today | [Apply](https://job-boards.greenhouse.io/instabase/jobs/8548929002) | needs_user_review |
"""
        with tempfile.TemporaryDirectory() as tmp:
            application_pack_dir = Path(tmp) / "application-packs" / "2026-06-04"
            expected_role_folder = application_pack_dir / "instabase-full-stack-software-engineer-new-grad"
            result = generate_from_report(
                markdown=markdown,
                source_resume=MAIN_RESUME_DOCX,
                dashboard_dir=Path(tmp) / "dashboard",
                application_pack_dir=application_pack_dir,
                limit=1,
                verify_links=False,
            )
            role = result["pack"]["top_roles"][0]
            evidence_uri = role["source_url"]
            evidence_path = Path(evidence_uri.replace("file://", ""))
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            expected_application_pack_url = expected_role_folder.resolve().as_uri()
            self.assertTrue(expected_role_folder.exists())

        self.assertEqual(evidence["source_resume"], str(MAIN_RESUME_DOCX))
        expected_profile = MAIN_RESUME_DOCX.parent / "transcript-profile.json"
        self.assertEqual(evidence["transcript_profile"], str(expected_profile))
        self.assertTrue(Path(evidence["transcript_profile"]).exists())
        self.assertEqual(role["application_pack_url"], expected_application_pack_url)

    def test_generate_from_report_blocks_resume_links_when_validation_fails(self):
        markdown = """
## Apply Today Top 10

| # | Company | Title | Location | Fit | Salary | Status | Link | Tailoring |
|---:|---|---|---|---:|---|---|---|---|
| 1 | Instabase | Full-stack Software Engineer (New Grad) | San Francisco, CA | 95 | $140,000-$145,455 | apply_today | [Apply](https://job-boards.greenhouse.io/instabase/jobs/8548929002) | needs_user_review |
"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifacts = SimpleNamespace(
                docx_path=tmp_path / "pack" / "Ayush-Yadav-Instabase-Resume.docx",
                pdf_path=tmp_path / "pack" / "Ayush-Yadav-Instabase-Resume.pdf",
                evidence_path=tmp_path / "pack" / "evidence-ledger.json",
                validation_path=tmp_path / "pack" / "validation-report.json",
            )
            with (
                patch("job_scout.generator.create_tailored_resume", return_value=artifacts),
                patch("job_scout.generator.validate_resume_artifacts", return_value={"is_valid": False}),
            ):
                result = generate_from_report(
                    markdown=markdown,
                    source_resume=tmp_path / "source.docx",
                    dashboard_dir=tmp_path / "dashboard",
                    application_pack_dir=tmp_path / "application-packs",
                    limit=1,
                    verify_links=False,
                )

        role = result["pack"]["top_roles"][0]
        self.assertEqual(role["resume_pdf"], "")
        self.assertEqual(role["resume_docx"], "")
        self.assertEqual(role["resume_review_status"], "resume_validation_blocked")
        self.assertIn("resume validation blocked", role["manual_fields"])
        self.assertTrue(role["source_url"].startswith("file://"))
        self.assertTrue(role["validation_url"].startswith("file://"))
        self.assertTrue(role["application_pack_url"].startswith("file://"))

    @unittest.skipUnless(SOURCE_RESUME.exists(), "requires private original resume DOCX")
    def test_generate_from_report_creates_dashboard_and_resume_pack(self):
        markdown = """
## Apply Today Top 10

| # | Company | Title | Location | Fit | Salary | Status | Link | Tailoring |
|---:|---|---|---|---:|---|---|---|---|
| 1 | Instabase | Full-stack Software Engineer (New Grad) | San Francisco, CA | 95 | $140,000-$145,455 | apply_today | [Apply](https://job-boards.greenhouse.io/instabase/jobs/8548929002) | needs_user_review |
| 2 | IXL Learning | Software Engineer - New Grad | San Mateo, CA | 76 | not checked | apply_today | [Apply](https://ixl.com/company/careers?gh_jid=8530389002) | needs_user_review |
| 3 | IXL Learning | Software Engineer - New Grad | Raleigh, NC | 75 | not checked | apply_today | [Apply](https://ixl.com/company/careers?gh_jid=8530542002) | needs_user_review |

## Watchlist Next 40

| # | Company | Title | Location | Fit | Salary | Status / note | Link |
|---:|---|---|---|---:|---|---|---|
| 11 | Amazon / Twitch | Software Engineer I | Seattle, WA | 90 | $110,500-$160,000 | manual review required. | [Open](https://amazon.jobs/en/jobs/3141336/software-engineer-i) |
"""
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_from_report(
                markdown=markdown,
                source_resume=SOURCE_RESUME,
                dashboard_dir=Path(tmp) / "dashboard",
                application_pack_dir=Path(tmp) / "application-packs" / "2026-05-30",
                limit=4,
                verify_links=False,
            )

            self.assertTrue(result["dashboard"]["index_path"].exists())
            self.assertTrue(result["dashboard"]["data_path"].exists())
            self.assertEqual(len(result["pack"]["top_roles"]), 4)
            first = result["pack"]["top_roles"][0]
            self.assertTrue(first["resume_pdf"].startswith("file://"))
            self.assertTrue(first["resume_docx"].startswith("file://"))
            self.assertEqual(result["pack"]["easy_apply"], [])
            self.assertTrue((Path(tmp) / "application-packs" / "2026-05-30" / "instabase-full-stack-software-engineer-new-grad" / "validation-report.json").exists())
            self.assertEqual(len(list((Path(tmp) / "application-packs" / "2026-05-30").glob("*/validation-report.json"))), 4)
            self.assertEqual(result["pack"]["run_date"], "2026-05-30")
            self.assertTrue(result["dashboard"]["run_path"].as_posix().endswith("data/runs/2026-05-30.json"))

    @unittest.skipUnless(SOURCE_RESUME.exists(), "requires private original resume DOCX")
    def test_generate_from_report_skips_stale_roles_before_creating_resume_packs(self):
        markdown = """
## Apply Today Top 10

| # | Company | Title | Location | Fit | Salary | Status | Link | Tailoring |
|---:|---|---|---|---:|---|---|---|---|
| 1 | BrokenCo | Software Engineer (New Grad) | Remote | 99 | not checked | page_not_found | [Apply](https://example.com/broken) | needs_user_review |
| 2 | LiveCo | Software Engineer (New Grad) | Remote | 95 | not checked | direct_detail_verified_manual_review | [Apply](https://example.com/live) | needs_user_review |

## Watchlist Next 40

| # | Company | Title | Location | Fit | Salary | Status / note | Link |
|---:|---|---|---|---:|---|---|---|
| 11 | FillCo | Backend Engineer | Remote | 90 | not checked | manual review required. | [Open](https://example.com/fill) |
"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = generate_from_report(
                markdown=markdown,
                source_resume=SOURCE_RESUME,
                dashboard_dir=tmp_path / "dashboard",
                application_pack_dir=tmp_path / "application-packs" / "2026-06-04",
                limit=2,
                verify_links=False,
            )

            companies = [role["company"] for role in result["pack"]["top_roles"]]
            pack_folders = sorted(path.name for path in (tmp_path / "application-packs" / "2026-06-04").iterdir())

        self.assertEqual(companies, ["LiveCo", "FillCo"])
        self.assertEqual(result["pack"]["stale"], [])
        self.assertEqual([role["company"] for role in result["pack"]["excluded_stale"]], ["BrokenCo"])
        self.assertNotIn("brokenco-software-engineer-new-grad", pack_folders)
        self.assertIn("liveco-software-engineer-new-grad", pack_folders)
        self.assertIn("fillco-backend-engineer", pack_folders)

    @unittest.skipUnless(SOURCE_RESUME.exists(), "requires private original resume DOCX")
    def test_generate_from_report_passes_run_date_to_dashboard_outputs(self):
        markdown = """
## Apply Today Top 10

| # | Company | Title | Location | Fit | Salary | Status | Link | Tailoring |
|---:|---|---|---|---:|---|---|---|---|
| 1 | Instabase | Full-stack Software Engineer (New Grad) | San Francisco, CA | 95 | $140,000-$145,455 | apply_today | [Apply](https://job-boards.greenhouse.io/instabase/jobs/8548929002) | needs_user_review |
"""
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_from_report(
                markdown=markdown,
                source_resume=SOURCE_RESUME,
                dashboard_dir=Path(tmp) / "dashboard",
                application_pack_dir=Path(tmp) / "application-packs" / "2026-06-04",
                limit=1,
                verify_links=False,
                run_date="2026-06-04",
            )

            run_path = result["dashboard"]["run_path"]
            run_data = json.loads(run_path.read_text(encoding="utf-8"))

        self.assertEqual(result["pack"]["run_date"], "2026-06-04")
        self.assertTrue(run_path.as_posix().endswith("data/runs/2026-06-04.json"))
        self.assertEqual(run_data["run_date"], "2026-06-04")


if __name__ == "__main__":
    unittest.main()
