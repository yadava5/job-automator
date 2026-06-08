import unittest
import urllib.error
from unittest.mock import patch

from job_scout.link_checker import classify_fetch_result, verify_url


class LinkCheckerTests(unittest.TestCase):
    def test_stale_patterns_are_not_apply_ready(self):
        result = classify_fetch_result(
            requested_url="https://job-boards.greenhouse.io/flex/jobs/example",
            final_url="https://job-boards.greenhouse.io/flex?error=true",
            status_code=200,
            html="<title>Jobs at Flex</title>",
            expected_company="Flex",
            expected_title="Software Engineer",
            report_status="apply_today",
        )

        self.assertEqual(result["verification_status"], "redirected_to_board_stale")
        self.assertFalse(result["apply_ready"])

    def test_http_error_status_is_classified_as_page_not_found(self):
        record = {
            "company": "ClosedCo",
            "title": "Software Engineer",
            "report_status": "apply_today",
            "apply_url": "https://example.com/jobs/closed",
            "manual_fields": [],
        }
        error = urllib.error.HTTPError(
            url=record["apply_url"],
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

        with patch("job_scout.link_checker.urllib.request.urlopen", side_effect=error):
            result = verify_url(record)

        self.assertEqual(result["verification_status"], "page_not_found")
        self.assertNotEqual(result["verification_status"], "not_checked_research_only")

    def test_incidental_not_found_text_does_not_make_matching_form_stale(self):
        result = classify_fetch_result(
            requested_url="https://jobs.ashbyhq.com/decagon/2a435dd5",
            final_url="https://jobs.ashbyhq.com/decagon/2a435dd5",
            status_code=200,
            html=(
                "<h1>Agent Software Engineer - New Grad (2026 Start)</h1>"
                '<script>{"directApply":true,"__autoSerializationID":"FormSubmit"}</script>'
                "<script>const messages = ['Candidate not found']; const data = {isListed:false};</script>"
            ),
            expected_company="Decagon",
            expected_title="Agent Software Engineer - New Grad (2026 Start)",
            report_status="apply_today_manual_review",
        )

        self.assertEqual(result["verification_status"], "direct_detail_verified_manual_review")
        self.assertFalse(result["apply_ready"])

    def test_direct_matching_form_can_be_apply_ready_when_report_is_not_manual(self):
        result = classify_fetch_result(
            requested_url="https://job-boards.greenhouse.io/instabase/jobs/8548929002",
            final_url="https://job-boards.greenhouse.io/instabase/jobs/8548929002",
            status_code=200,
            html="<h1>Full-stack Software Engineer (New Grad)</h1><button>Apply for this job</button>",
            expected_company="Instabase",
            expected_title="Full-stack Software Engineer (New Grad)",
            report_status="apply_today",
        )

        self.assertEqual(result["verification_status"], "direct_form_verified")
        self.assertTrue(result["apply_ready"])

    def test_manual_report_status_stays_manual_even_when_page_loads(self):
        result = classify_fetch_result(
            requested_url="https://jobs.ashbyhq.com/gigaml/7314/application",
            final_url="https://jobs.ashbyhq.com/gigaml/7314/application",
            status_code=200,
            html="<h1>Software Engineer (New Grads)</h1><button>Submit Application</button>",
            expected_company="Giga",
            expected_title="Software Engineer (New Grads)",
            report_status="apply_today_manual_review",
        )

        self.assertEqual(result["verification_status"], "direct_detail_verified_manual_review")
        self.assertFalse(result["apply_ready"])

    def test_sensitive_status_note_stays_manual_even_when_form_loads(self):
        result = classify_fetch_result(
            requested_url="https://job-boards.greenhouse.io/embed/job_app?for=unity3d&token=7947300",
            final_url="https://job-boards.greenhouse.io/embed/job_app?for=unity3d&token=7947300",
            status_code=200,
            html="<h1>Machine Learning Engineer, User Understanding</h1><button>Apply for this job</button>",
            expected_company="Unity",
            expected_title="Machine Learning Engineer, User Understanding (Entry-Level / New Grad)",
            report_status="Strong ML/new-grad role; sponsorship/export-control/transcript consent and commute questions are manual.",
        )

        self.assertEqual(result["verification_status"], "direct_detail_verified_manual_review")
        self.assertFalse(result["apply_ready"])

    def test_sensitive_page_text_stays_manual_even_when_report_omits_caveat(self):
        result = classify_fetch_result(
            requested_url="https://job-boards.greenhouse.io/example/jobs/123",
            final_url="https://job-boards.greenhouse.io/example/jobs/123",
            status_code=200,
            html=(
                "<h1>Software Engineer New Grad</h1>"
                "<label>Will you now or in the future require visa sponsorship?</label>"
                "<button>Apply for this job</button>"
            ),
            expected_company="Example",
            expected_title="Software Engineer New Grad",
            report_status="apply_today",
        )

        self.assertEqual(result["verification_status"], "direct_detail_verified_manual_review")
        self.assertFalse(result["apply_ready"])


if __name__ == "__main__":
    unittest.main()
