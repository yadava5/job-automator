import unittest

from job_scout.link_pack import build_application_pack


class LinkPackTests(unittest.TestCase):
    def test_manual_review_overrides_easy_apply_for_validation_blocks(self):
        records = [
            {
                "company": "BlockedCo",
                "title": "Software Engineer",
                "location": "San Francisco, CA",
                "fit_score": 99,
                "apply_url": "https://example.com/blocked",
                "verified_url": "https://example.com/blocked",
                "verification_status": "direct_form_verified",
                "manual_fields": [],
                "resume_review_status": "resume_validation_blocked",
            },
            {
                "company": "ManualCo",
                "title": "Software Engineer",
                "location": "New York, NY",
                "fit_score": 98,
                "apply_url": "https://example.com/manual",
                "verified_url": "https://example.com/manual",
                "verification_status": "direct_form_verified",
                "manual_fields": ["work authorization"],
                "resume_review_status": "needs_user_review",
            },
            {
                "company": "StaleCo",
                "title": "Software Engineer",
                "location": "Remote",
                "fit_score": 97,
                "apply_url": "https://example.com/stale",
                "verified_url": "https://example.com/stale",
                "verification_status": "redirected_to_board_stale",
                "manual_fields": ["resume validation blocked"],
                "resume_review_status": "resume_validation_blocked",
            },
        ]

        pack = build_application_pack(records, limit=30)

        self.assertEqual(pack["easy_apply"], [])
        self.assertEqual([item["company"] for item in pack["manual_review"]], ["BlockedCo", "ManualCo"])
        self.assertEqual([item["company"] for item in pack["stale"]], ["StaleCo"])

    def test_easy_apply_contains_only_same_run_direct_verified_links(self):
        records = [
            {
                "company": "Instabase",
                "title": "Full-stack Software Engineer (New Grad)",
                "location": "San Francisco, CA",
                "fit_score": 95,
                "salary": "$140,000-$145,455",
                "apply_url": "https://job-boards.greenhouse.io/instabase/jobs/8548929002",
                "verified_url": "https://job-boards.greenhouse.io/instabase/jobs/8548929002",
                "verification_status": "direct_form_verified",
                "last_checked": "2026-05-30T02:00:00-04:00",
                "manual_fields": [],
                "resume_pdf": "/tmp/Ayush-Yadav-Instabase-Resume.pdf",
                "resume_docx": "/tmp/Ayush-Yadav-Instabase-Resume.docx",
                "source_url": "https://github.com/SimplifyJobs/New-Grad-Positions",
            },
            {
                "company": "Quora",
                "title": "Software Engineer New Grad 2025-2026 - Data Infrastructure",
                "location": "Remote US",
                "fit_score": 92,
                "apply_url": "https://jobs.ashbyhq.com/quora/6d5ce948-148e-4b0b-8623-4dbc4517a743",
                "verified_url": "",
                "verification_status": "js_only_manual_browser_required",
                "last_checked": "2026-05-30T02:00:00-04:00",
                "manual_fields": ["sponsorship"],
                "resume_pdf": "",
                "resume_docx": "",
                "source_url": "https://github.com/SimplifyJobs/New-Grad-Positions",
            },
            {
                "company": "Flex",
                "title": "Software Engineer - Backend",
                "location": "Remote",
                "fit_score": 80,
                "apply_url": "https://job-boards.greenhouse.io/flex/jobs/example",
                "verified_url": "https://job-boards.greenhouse.io/flex?error=true",
                "verification_status": "redirected_to_board_stale",
                "last_checked": "2026-05-30T02:00:00-04:00",
                "manual_fields": [],
                "resume_pdf": "",
                "resume_docx": "",
                "source_url": "https://github.com/cvrve/New-Grad",
            },
        ]

        pack = build_application_pack(records, limit=30)

        self.assertEqual([item["company"] for item in pack["easy_apply"]], ["Instabase"])
        self.assertEqual([item["company"] for item in pack["manual_review"]], ["Quora"])
        self.assertEqual([item["company"] for item in pack["stale"]], ["Flex"])
        self.assertEqual(pack["easy_apply"][0]["primary_url"], records[0]["verified_url"])
        self.assertNotIn("Quora", [item["company"] for item in pack["easy_apply"]])

    def test_page_not_found_records_land_in_stale(self):
        records = [
            {
                "company": "ClosedCo",
                "title": "Software Engineer",
                "location": "Remote",
                "fit_score": 90,
                "apply_url": "https://example.com/jobs/closed",
                "verified_url": "https://example.com/jobs/closed",
                "verification_status": "page_not_found",
                "manual_fields": ["link/manual review"],
            }
        ]

        pack = build_application_pack(records, limit=30)

        self.assertEqual(pack["easy_apply"], [])
        self.assertEqual(pack["manual_review"], [])
        self.assertEqual([item["company"] for item in pack["stale"]], ["ClosedCo"])

    def test_pack_limits_total_top_roles_without_dropping_status_buckets(self):
        records = [
            {
                "company": f"Company {idx}",
                "title": "Software Engineer New Grad",
                "location": "New York, NY",
                "fit_score": 100 - idx,
                "apply_url": f"https://example.com/{idx}",
                "verified_url": f"https://example.com/{idx}",
                "verification_status": "direct_form_verified",
                "last_checked": "2026-05-30T02:00:00-04:00",
                "manual_fields": [],
                "resume_pdf": "",
                "resume_docx": "",
                "source_url": "https://example.com/source",
            }
            for idx in range(35)
        ]

        pack = build_application_pack(records, limit=30)

        self.assertEqual(len(pack["top_roles"]), 30)
        self.assertEqual(pack["top_roles"][0]["company"], "Company 0")
        self.assertEqual(pack["top_roles"][-1]["company"], "Company 29")


if __name__ == "__main__":
    unittest.main()
