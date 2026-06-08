import json
import tempfile
import unittest
from pathlib import Path

from job_scout.dashboard import write_dashboard


class DashboardTests(unittest.TestCase):
    def test_dashboard_writes_static_html_and_json_with_apply_and_resume_links(self):
        pack = {
            "run_id": "daily-new-grad-job-scout-2026-05-30T020000-0400",
            "generated_at": "2026-05-30T02:00:00-04:00",
            "top_roles": [
                {
                    "rank": 1,
                    "company": "Instabase",
                    "title": "Full-stack Software Engineer (New Grad)",
                    "location": "San Francisco, CA",
                    "fit_score": 95,
                    "salary": "$140,000-$145,455",
                    "primary_url": "https://job-boards.greenhouse.io/instabase/jobs/8548929002",
                    "verification_status": "direct_form_verified",
                    "manual_fields": [],
                    "resume_pdf": "/tmp/Ayush-Yadav-Instabase-Resume.pdf",
                    "resume_docx": "/tmp/Ayush-Yadav-Instabase-Resume.docx",
                    "source_url": "https://github.com/SimplifyJobs/New-Grad-Positions",
                }
            ],
            "easy_apply": [],
            "manual_review": [],
            "research": [],
            "stale": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            result = write_dashboard(pack, Path(tmp))
            html = result["index_path"].read_text(encoding="utf-8")
            data = json.loads(result["data_path"].read_text(encoding="utf-8"))

        self.assertIn("Top 20-30 Today", html)
        self.assertIn("Easy Apply Pack", html)
        self.assertIn("Instabase", html)
        self.assertIn("Open Apply Link", html)
        self.assertIn("Resume PDF", html)
        self.assertEqual(data["top_roles"][0]["company"], "Instabase")
        self.assertTrue(result["index_path"].name.endswith(".html"))

    def test_manual_and_stale_rows_do_not_use_easy_apply_button_wording(self):
        pack = {
            "top_roles": [
                {
                    "rank": 1,
                    "company": "Giga",
                    "title": "Software Engineer (New Grads)",
                    "location": "New York, NY",
                    "fit_score": 96,
                    "salary": "$160,000-$250,000",
                    "primary_url": "https://jobs.ashbyhq.com/gigaml/example/application",
                    "verification_status": "direct_detail_verified_manual_review",
                    "manual_fields": ["sponsorship", "link/manual review"],
                    "resume_pdf": "",
                    "resume_docx": "",
                    "source_url": "",
                },
                {
                    "rank": 2,
                    "company": "Flex",
                    "title": "Software Engineer",
                    "location": "Remote",
                    "fit_score": 80,
                    "salary": "",
                    "primary_url": "https://job-boards.greenhouse.io/flex?error=true",
                    "verification_status": "redirected_to_board_stale",
                    "manual_fields": [],
                    "resume_pdf": "",
                    "resume_docx": "",
                    "source_url": "",
                },
            ],
            "easy_apply": [],
            "manual_review": [],
            "research": [],
            "stale": [],
        }
        pack["manual_review"] = [pack["top_roles"][0]]
        pack["stale"] = [pack["top_roles"][1]]

        with tempfile.TemporaryDirectory() as tmp:
            result = write_dashboard(pack, Path(tmp))
            html = result["index_path"].read_text(encoding="utf-8")

        self.assertIn("Review Link", html)
        self.assertIn("Stale Link", html)
        self.assertIn("Review required before applying", html)
        self.assertIn("Stale or removed during same-run check", html)
        self.assertIn("Check: Sponsorship/work authorization", html)
        self.assertIn("open and confirm application page", html)
        self.assertNotIn("Open Apply Link</a>", html)
        self.assertNotIn('<p class="status">direct_detail_verified_manual_review</p>', html)
        self.assertNotIn('<p class="status">redirected_to_board_stale</p>', html)

    def test_validation_blocked_direct_form_role_renders_review_link(self):
        pack = {
            "top_roles": [
                {
                    "rank": 1,
                    "company": "BlockedCo",
                    "title": "Software Engineer",
                    "location": "San Francisco, CA",
                    "fit_score": 95,
                    "salary": "",
                    "primary_url": "https://example.com/apply",
                    "verification_status": "direct_form_verified",
                    "manual_fields": ["resume validation blocked"],
                    "resume_review_status": "resume_validation_blocked",
                    "resume_pdf": "",
                    "resume_docx": "",
                    "source_url": "file:///tmp/evidence-ledger.json",
                    "validation_url": "file:///tmp/validation-report.json",
                }
            ],
            "easy_apply": [],
            "manual_review": [],
            "research": [],
            "stale": [],
        }
        pack["manual_review"] = [pack["top_roles"][0]]

        with tempfile.TemporaryDirectory() as tmp:
            result = write_dashboard(pack, Path(tmp))
            html = result["index_path"].read_text(encoding="utf-8")

        self.assertIn("Review Link", html)
        self.assertNotIn("Open Apply Link", html)

    def test_direct_apply_verified_role_renders_open_apply_link(self):
        pack = {
            "top_roles": [
                {
                    "rank": 1,
                    "company": "ApplyCo",
                    "title": "Software Engineer",
                    "location": "Remote",
                    "fit_score": 91,
                    "salary": "",
                    "primary_url": "https://example.com/direct-apply",
                    "verification_status": "direct_apply_verified",
                    "manual_fields": [],
                    "resume_review_status": "needs_user_review",
                    "resume_pdf": "",
                    "resume_docx": "",
                    "source_url": "",
                }
            ],
            "easy_apply": [],
            "manual_review": [],
            "research": [],
            "stale": [],
        }
        pack["easy_apply"] = [pack["top_roles"][0]]

        with tempfile.TemporaryDirectory() as tmp:
            result = write_dashboard(pack, Path(tmp))
            html = result["index_path"].read_text(encoding="utf-8")

        self.assertIn("Open Apply Link", html)
        self.assertNotIn("Review Link", html)

    def test_public_dashboard_removes_all_private_file_links_from_html_and_json(self):
        pack = {
            "run_id": "job-scout-dashboard-2026-06-07T120000",
            "generated_at": "2026-06-07T12:00:00-04:00",
            "run_date": "2026-06-07",
            "top_roles": [
                {
                    "rank": 1,
                    "company": "Giga",
                    "title": "Software Engineer (New Grads)",
                    "location": "New York, NY",
                    "fit_score": 96,
                    "salary": "$160,000-$250,000/year + equity",
                    "verification_status": "direct_detail_verified_manual_review",
                    "manual_fields": ["application questions"],
                    "primary_url": "https://jobs.ashbyhq.com/gigaml/example",
                    "application_pack_url": "file:///Users/private/private-pack",
                    "resume_pdf": "file:///Users/private/private.pdf",
                    "resume_docx": "file:///Users/private/private.docx",
                    "source_url": "file:///Users/private/evidence-ledger.json",
                    "evidence_url": "file:///Users/private/alternate-evidence-ledger.json",
                    "validation_url": "file:///Users/private/validation-report.json",
                }
            ],
            "easy_apply": [],
            "manual_review": [],
            "research": [],
            "stale": [],
            "excluded_stale": [
                {
                    "rank": 2,
                    "company": "StalePrivate",
                    "title": "Engineer",
                    "primary_url": "https://example.com/stale",
                    "application_pack_url": "file:///Users/private/stale-pack",
                    "resume_pdf": "file:///Users/private/stale.pdf",
                    "resume_docx": "file:///Users/private/stale.docx",
                    "source_url": "file:///Users/private/stale-evidence-ledger.json",
                    "evidence_url": "file:///Users/private/stale-alternate-evidence-ledger.json",
                    "validation_url": "file:///Users/private/stale-validation-report.json",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = write_dashboard(pack, output_dir, run_date="2026-06-07", public=True)
            paths = [
                result["index_path"],
                result["data_path"],
                result["manifest_path"],
                result["run_path"],
            ]
            combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
            latest = json.loads(result["data_path"].read_text(encoding="utf-8"))
            run_data = json.loads(result["run_path"].read_text(encoding="utf-8"))

        self.assertIn("https://jobs.ashbyhq.com/gigaml/example", combined)
        for forbidden in (
            "file://",
            "/Users/private",
            "evidence-ledger",
            "validation-report",
            "private.pdf",
            "private.docx",
            "stale.pdf",
            "stale.docx",
        ):
            self.assertNotIn(forbidden, combined)
        self.assertEqual(latest["top_roles"][0]["application_pack_url"], "")
        self.assertEqual(latest["top_roles"][0]["resume_pdf"], "")
        self.assertEqual(latest["top_roles"][0]["resume_docx"], "")
        self.assertEqual(latest["top_roles"][0]["source_url"], "")
        self.assertEqual(latest["top_roles"][0]["evidence_url"], "")
        self.assertEqual(latest["top_roles"][0]["validation_url"], "")
        self.assertEqual(run_data["excluded_stale"][0]["application_pack_url"], "")
        self.assertEqual(run_data["excluded_stale"][0]["resume_pdf"], "")

    def test_public_dashboard_sanitizes_existing_run_files_before_preserving_manifest(self):
        stale_pack = {
            "run_id": "job-scout-dashboard-2026-06-06T120000",
            "generated_at": "2026-06-06T12:00:00-04:00",
            "run_date": "2026-06-06",
            "top_roles": [
                {
                    "rank": 1,
                    "company": "OldPrivate",
                    "title": "Engineer",
                    "primary_url": "https://example.com/old",
                    "verification_status": "direct_form_verified",
                    "manual_fields": [],
                    "application_pack_url": "file:///Users/private/old-pack",
                    "resume_pdf": "file:///Users/private/old.pdf",
                    "resume_docx": "file:///Users/private/old.docx",
                    "source_url": "file:///Users/private/old-evidence-ledger.json",
                    "evidence_url": "file:///Users/private/old-alt-evidence-ledger.json",
                    "validation_url": "file:///Users/private/old-validation-report.json",
                }
            ],
            "easy_apply": [],
            "manual_review": [],
            "research": [],
            "stale": [],
        }
        current_pack = {
            "run_id": "job-scout-dashboard-2026-06-07T120000",
            "generated_at": "2026-06-07T12:00:00-04:00",
            "run_date": "2026-06-07",
            "top_roles": [
                {
                    "rank": 1,
                    "company": "NewPublic",
                    "title": "Engineer",
                    "primary_url": "https://example.com/new",
                    "verification_status": "direct_form_verified",
                    "manual_fields": [],
                }
            ],
            "easy_apply": [],
            "manual_review": [],
            "research": [],
            "stale": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            runs_dir = output_dir / "data" / "runs"
            runs_dir.mkdir(parents=True)
            (runs_dir / "2026-06-06.json").write_text(json.dumps(stale_pack, indent=2), encoding="utf-8")
            result = write_dashboard(current_pack, output_dir, run_date="2026-06-07", public=True)
            paths = [
                result["index_path"],
                result["data_path"],
                result["manifest_path"],
                result["run_path"],
                runs_dir / "2026-06-06.json",
            ]
            combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
            prior_run = json.loads((runs_dir / "2026-06-06.json").read_text(encoding="utf-8"))

        self.assertIn("OldPrivate", combined)
        self.assertIn("https://example.com/old", combined)
        for forbidden in ("file://", "/Users/private", "evidence-ledger", "validation-report", "old.pdf", "old.docx"):
            self.assertNotIn(forbidden, combined)
        self.assertEqual(prior_run["top_roles"][0]["application_pack_url"], "")
        self.assertEqual(prior_run["top_roles"][0]["evidence_url"], "")

    def test_public_dashboard_sanitizes_existing_run_in_place_when_embedded_run_date_mismatches(self):
        stale_pack = {
            "run_id": "job-scout-dashboard-2026-06-06T120000",
            "generated_at": "2026-06-06T12:00:00-04:00",
            "run_date": "../private",
            "top_roles": [
                {
                    "rank": 1,
                    "company": "MismatchPrivate",
                    "title": "Engineer",
                    "primary_url": "https://example.com/mismatch",
                    "verification_status": "direct_form_verified",
                    "manual_fields": [],
                    "application_pack_url": "file:///Users/private/mismatch-pack",
                    "resume_pdf": "file:///Users/private/mismatch.pdf",
                    "resume_docx": "file:///Users/private/mismatch.docx",
                    "source_url": "file:///Users/private/mismatch-evidence-ledger.json",
                    "evidence_url": "file:///Users/private/mismatch-alt-evidence-ledger.json",
                    "validation_url": "file:///Users/private/mismatch-validation-report.json",
                }
            ],
            "easy_apply": [],
            "manual_review": [],
            "research": [],
            "stale": [],
        }
        current_pack = {
            "run_id": "job-scout-dashboard-2026-06-07T120000",
            "generated_at": "2026-06-07T12:00:00-04:00",
            "run_date": "2026-06-07",
            "top_roles": [],
            "easy_apply": [],
            "manual_review": [],
            "research": [],
            "stale": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            runs_dir = output_dir / "data" / "runs"
            runs_dir.mkdir(parents=True)
            original_path = runs_dir / "2026-06-06.json"
            original_path.write_text(json.dumps(stale_pack, indent=2), encoding="utf-8")
            result = write_dashboard(current_pack, output_dir, run_date="2026-06-07", public=True)
            combined = "\n".join(
                path.read_text(encoding="utf-8")
                for path in [result["index_path"], result["data_path"], result["manifest_path"], original_path]
            )
            original_exists = original_path.exists()
            escaped_path_created = (output_dir / "data" / "private.json").exists()

        self.assertTrue(original_exists)
        self.assertFalse(escaped_path_created)
        self.assertIn("MismatchPrivate", combined)
        for forbidden in ("file://", "/Users/private", "evidence-ledger", "validation-report", "mismatch.pdf"):
            self.assertNotIn(forbidden, combined)

    def test_public_dashboard_removes_wrong_shaped_orphan_run_files_before_publish(self):
        current_pack = {
            "run_id": "job-scout-dashboard-2026-06-07T120000",
            "generated_at": "2026-06-07T12:00:00-04:00",
            "run_date": "2026-06-07",
            "top_roles": [],
            "easy_apply": [],
            "manual_review": [],
            "research": [],
            "stale": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            runs_dir = output_dir / "data" / "runs"
            runs_dir.mkdir(parents=True)
            malformed = runs_dir / "malformed.json"
            wrong_shape = runs_dir / "wrong-shape.json"
            malformed.write_text('{"private": "file:///Users/private/private.pdf"', encoding="utf-8")
            wrong_shape.write_text(
                json.dumps({"private": "file:///Users/private/private.pdf", "top_roles": "bad"}),
                encoding="utf-8",
            )

            result = write_dashboard(current_pack, output_dir, run_date="2026-06-07", public=True)
            public_files = sorted(path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*") if path.is_file())
            combined = "\n".join(path.read_text(encoding="utf-8") for path in output_dir.rglob("*") if path.is_file())

        self.assertFalse(malformed.exists())
        self.assertFalse(wrong_shape.exists())
        self.assertNotIn("data/runs/malformed.json", public_files)
        self.assertNotIn("data/runs/wrong-shape.json", public_files)
        self.assertIn(result["run_path"].relative_to(output_dir).as_posix(), public_files)
        for forbidden in ("file://", "/Users/private", "private.pdf"):
            self.assertNotIn(forbidden, combined)


class DashboardRunManifestTests(unittest.TestCase):
    def test_dashboard_writes_latest_run_file_and_manifest(self):
        pack = {
            "run_id": "job-scout-dashboard-2026-06-04T120000",
            "generated_at": "2026-06-04T12:00:00-04:00",
            "run_date": "2026-06-04",
            "top_roles": [],
            "easy_apply": [],
            "manual_review": [],
            "research": [],
            "stale": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            result = write_dashboard(pack, Path(tmp), run_date="2026-06-04")
            latest = json.loads(result["data_path"].read_text(encoding="utf-8"))
            manifest = json.loads(result["manifest_path"].read_text(encoding="utf-8"))
            run_data = json.loads(result["run_path"].read_text(encoding="utf-8"))
            html = result["index_path"].read_text(encoding="utf-8")

        self.assertEqual(latest["run_date"], "2026-06-04")
        self.assertEqual(run_data["run_date"], "2026-06-04")
        self.assertEqual(result["run_path"].as_posix().split("/")[-3:], ["data", "runs", "2026-06-04.json"])
        self.assertEqual(manifest["latest_run_date"], "2026-06-04")
        self.assertEqual(manifest["runs"][0]["run_date"], "2026-06-04")
        self.assertEqual(manifest["runs"][0]["data_path"], "data/runs/2026-06-04.json")
        self.assertIn('id="runSelect"', html)
        self.assertIn("data-run-selector", html)
        self.assertIn("data-run-line", html)
        self.assertIn("data-run-metrics", html)
        self.assertIn('data-metric="total"', html)
        self.assertIn('data-metric="easy"', html)
        self.assertIn('data-metric="manual"', html)
        self.assertIn('data-metric="stale"', html)
        self.assertIn("data-job-list", html)
        self.assertIn("window.JOB_SCOUT_MANIFEST", html)
        self.assertIn("window.JOB_SCOUT_RUNS", html)

    def test_dashboard_preserves_prior_runs_in_manifest_and_embedded_payload(self):
        older_pack = {
            "run_id": "job-scout-dashboard-2026-06-03T120000",
            "generated_at": "2026-06-03T12:00:00-04:00",
            "top_roles": [{"rank": 1, "company": "OlderCo", "title": "Engineer", "verification_status": "direct_apply_verified"}],
            "easy_apply": [{"rank": 1, "company": "OlderCo", "title": "Engineer", "verification_status": "direct_apply_verified"}],
            "manual_review": [],
            "research": [],
            "stale": [],
        }
        newer_pack = {
            "run_id": "job-scout-dashboard-2026-06-04T120000",
            "generated_at": "2026-06-04T12:00:00-04:00",
            "top_roles": [{"rank": 1, "company": "NewerCo", "title": "Engineer", "verification_status": "direct_form_verified"}],
            "easy_apply": [{"rank": 1, "company": "NewerCo", "title": "Engineer", "verification_status": "direct_form_verified"}],
            "manual_review": [],
            "research": [],
            "stale": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_dashboard(older_pack, output_dir, run_date="2026-06-03")
            (output_dir / "data" / "runs" / "broken.json").write_text("{not json", encoding="utf-8")
            result = write_dashboard(newer_pack, output_dir, run_date="2026-06-04")
            manifest = json.loads(result["manifest_path"].read_text(encoding="utf-8"))
            html = result["index_path"].read_text(encoding="utf-8")

        self.assertEqual([run["run_date"] for run in manifest["runs"]], ["2026-06-04", "2026-06-03"])
        self.assertIn('"2026-06-03"', html)
        self.assertIn('"2026-06-04"', html)
        self.assertIn("OlderCo", html)
        self.assertIn("NewerCo", html)

    def test_dashboard_ignores_existing_run_json_with_wrong_shape(self):
        pack = {
            "run_id": "job-scout-dashboard-2026-06-04T120000",
            "generated_at": "2026-06-04T12:00:00-04:00",
            "top_roles": [],
            "easy_apply": [],
            "manual_review": [],
            "research": [],
            "stale": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            runs_dir = output_dir / "data" / "runs"
            runs_dir.mkdir(parents=True)
            (runs_dir / "array.json").write_text("[]", encoding="utf-8")
            (runs_dir / "string.json").write_text('"not a run"', encoding="utf-8")
            (runs_dir / "dict.json").write_text('{"foo": "bar"}', encoding="utf-8")
            (runs_dir / "run-date-only.json").write_text('{"run_date": "2026-06-01"}', encoding="utf-8")
            (runs_dir / "wrong-bucket-type.json").write_text(
                '{"top_roles": 1, "easy_apply": [], "manual_review": [], "research": [], "stale": []}',
                encoding="utf-8",
            )
            (runs_dir / "wrong-role-item.json").write_text(
                '{"top_roles": ["bad"], "easy_apply": [], "manual_review": [], "research": [], "stale": []}',
                encoding="utf-8",
            )
            result = write_dashboard(pack, output_dir, run_date="2026-06-04")
            manifest = json.loads(result["manifest_path"].read_text(encoding="utf-8"))
            html = result["index_path"].read_text(encoding="utf-8")

        self.assertEqual([run["run_date"] for run in manifest["runs"]], ["2026-06-04"])
        self.assertIn('"2026-06-04"', html)
        self.assertNotIn('"dict"', html)
        self.assertNotIn('"2026-06-01"', html)
        self.assertNotIn('"wrong-bucket-type"', html)
        self.assertNotIn('"wrong-role-item"', html)

    def test_status_labels_and_optional_links_are_in_fallback_and_embedded_payload(self):
        direct_role = {
            "rank": 1,
            "company": "ApplyCo",
            "title": "Software Engineer",
            "location": "Remote",
            "fit_score": 91,
            "primary_url": "https://example.com/direct-apply",
            "verification_status": "direct_apply_verified",
            "manual_fields": [],
            "resume_review_status": "needs_user_review",
            "resume_pdf": "file:///tmp/apply.pdf",
            "resume_docx": "file:///tmp/apply.docx",
            "source_url": "file:///tmp/apply-evidence.json",
            "validation_url": "file:///tmp/apply-validation.json",
            "application_pack_url": "file:///tmp/apply-pack",
        }
        blocked_role = {
            "rank": 2,
            "company": "BlockedCo",
            "title": "Software Engineer",
            "primary_url": "https://example.com/blocked",
            "verification_status": "direct_form_verified",
            "manual_fields": ["resume validation blocked"],
            "resume_review_status": "resume_validation_blocked",
            "validation_url": "file:///tmp/blocked-validation.json",
            "application_pack_url": "file:///tmp/blocked-pack",
        }
        stale_role = {
            "rank": 3,
            "company": "StaleCo",
            "title": "Software Engineer",
            "primary_url": "https://example.com/stale",
            "verification_status": "redirected_to_board_stale",
            "manual_fields": [],
        }
        pack = {
            "run_id": "job-scout-dashboard-2026-06-04T120000",
            "generated_at": "2026-06-04T12:00:00-04:00",
            "top_roles": [direct_role, blocked_role, stale_role],
            "easy_apply": [direct_role],
            "manual_review": [blocked_role],
            "research": [],
            "stale": [stale_role],
        }

        with tempfile.TemporaryDirectory() as tmp:
            result = write_dashboard(pack, Path(tmp), run_date="2026-06-04")
            html = result["index_path"].read_text(encoding="utf-8")

        self.assertIn("Open Apply Link", html)
        self.assertIn("Review Link", html)
        self.assertIn("Stale Link", html)
        self.assertIn("Pack", html)
        self.assertIn("Resume PDF", html)
        self.assertIn("Resume DOCX", html)
        self.assertIn("Evidence", html)
        self.assertIn("Validation", html)
        self.assertIn('"status_label": "Open Apply Link"', html)
        self.assertIn('"status_label": "Review Link"', html)
        self.assertIn('"status_label": "Stale Link"', html)
        self.assertIn('"status_text": "Same-run apply link verified"', html)
        self.assertIn('"status_text": "Review required before applying"', html)
        self.assertIn('"status_text": "Stale or removed during same-run check"', html)
        self.assertIn('"validation_url": "file:///tmp/apply-validation.json"', html)
        self.assertIn('"application_pack_url": "file:///tmp/apply-pack"', html)

    def test_dashboard_renders_persistent_application_decision_controls(self):
        pack = {
            "run_id": "job-scout-dashboard-2026-06-04T120000",
            "generated_at": "2026-06-04T12:00:00-04:00",
            "top_roles": [
                {
                    "rank": 1,
                    "company": "ApplyCo",
                    "title": "Software Engineer",
                    "location": "Remote",
                    "fit_score": 91,
                    "primary_url": "https://example.com/direct-apply",
                    "verification_status": "direct_apply_verified",
                    "manual_fields": [],
                    "resume_review_status": "needs_user_review",
                }
            ],
            "easy_apply": [],
            "manual_review": [],
            "research": [],
            "stale": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            result = write_dashboard(pack, Path(tmp), run_date="2026-06-04")
            html = result["index_path"].read_text(encoding="utf-8")

        self.assertIn("data-decision-controls", html)
        self.assertIn('<link rel="icon" href="data:,">', html)
        self.assertIn("Applied", html)
        self.assertIn("Not Applied", html)
        self.assertIn("Link Not Working", html)
        self.assertIn("jobScoutDecisions:v1", html)
        self.assertIn('"role_key": "2026-06-04|1|ApplyCo|Software Engineer"', html)
        self.assertIn("if (root.matches && root.matches(\"[data-decision-controls]\"))", html)
        self.assertIn("decisionGroups.push(root)", html)

    def test_dashboard_renders_decision_export_and_import_controls(self):
        pack = {
            "run_id": "job-scout-dashboard-2026-06-07T120000",
            "generated_at": "2026-06-07T12:00:00-04:00",
            "run_date": "2026-06-07",
            "top_roles": [
                {
                    "rank": 1,
                    "company": "Giga",
                    "title": "Software Engineer (New Grads)",
                    "location": "New York, NY",
                    "fit_score": 96,
                    "salary": "$160,000-$250,000/year + equity",
                    "verification_status": "direct_detail_verified_manual_review",
                    "manual_fields": [],
                    "primary_url": "https://jobs.ashbyhq.com/gigaml/example",
                    "resume_pdf": "",
                    "resume_docx": "",
                }
            ],
            "easy_apply": [],
            "manual_review": [],
            "research": [],
            "stale": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            result = write_dashboard(pack, Path(tmp), run_date="2026-06-07")
            html = result["index_path"].read_text(encoding="utf-8")

        self.assertIn("data-export-decisions", html)
        self.assertIn("data-import-decisions", html)
        self.assertIn("jobScoutDecisions:v1", html)
        self.assertIn("download = `job-scout-decisions-${new Date().toISOString().slice(0, 10)}.json`", html)
        self.assertIn("reader.readAsText(file)", html)
        self.assertIn("const ALLOWED_DECISIONS = new Set([\"applied\", \"not_applied\", \"link_not_working\"])", html)
        self.assertIn("const knownRoleKeys = new Set()", html)
        self.assertIn("sanitizeImportedDecisions(parsed)", html)
        self.assertIn("return sanitizeImportedDecisions(parsed)", html)
        self.assertIn("if (ALLOWED_DECISIONS.has(value))", html)
        self.assertIn("if (!ALLOWED_DECISIONS.has(button.dataset.decisionChoice))", html)
        self.assertIn("decisions[controls.dataset.roleKey] || \"not_applied\"", html)
        self.assertIn("if (!ALLOWED_DECISIONS.has(value))", html)
        self.assertIn('<button type="button" class="import-decisions" data-import-decisions-trigger>Import decisions</button>', html)
        self.assertIn('<input type="file" accept="application/json" data-import-decisions aria-label="Import decisions file">', html)
        self.assertIn('document.querySelector("[data-import-decisions-trigger]")?.addEventListener("click"', html)


if __name__ == "__main__":
    unittest.main()
