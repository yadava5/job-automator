import unittest

from job_scout.report_parser import parse_latest_report


class ReportParserTests(unittest.TestCase):
    def test_parse_apply_and_watchlist_tables_into_role_records(self):
        markdown = """
## Apply Today Top 10

| # | Company | Title | Location | Fit | Salary | Status | Link | Tailoring |
|---:|---|---|---|---:|---|---|---|---|
| 1 | Instabase | Full-stack Software Engineer (New Grad) | San Francisco, CA | 95 | $140,000-$145,455 | apply_today | [Apply](https://job-boards.greenhouse.io/instabase/jobs/8548929002) | needs_user_review |
| 2 | Quora | Software Engineer New Grad | Remote US | 92 | $97,600-$139,000 | apply_today_secondary_manual_review | [Apply](https://jobs.ashbyhq.com/quora/example) | not_started |

## Watchlist Next 40

| # | Company | Title | Location | Fit | Salary | Status / note | Link |
|---:|---|---|---|---:|---|---|---|
| 11 | Amazon / Twitch | Software Engineer I | Seattle, WA | 90 | $110,500-$160,000 | Redirects to Twitch career site; manual review. | [Open](https://amazon.jobs/en/jobs/3141336/software-engineer-i) |
"""

        roles = parse_latest_report(markdown)

        self.assertEqual(len(roles), 3)
        self.assertEqual(roles[0]["company"], "Instabase")
        self.assertEqual(roles[0]["verification_status"], "not_checked_research_only")
        self.assertEqual(roles[1]["verification_status"], "apply_today_secondary_manual_review")
        self.assertEqual(roles[2]["verification_status"], "direct_detail_verified_manual_review")
        self.assertEqual(roles[0]["apply_url"], "https://job-boards.greenhouse.io/instabase/jobs/8548929002")

    def test_pipe_separated_title_fragments_do_not_shift_columns(self):
        markdown = """
## Apply Today Top 10

| # | Company | Title | Location | Fit | Salary | Status | Link | Tailoring |
|---:|---|---|---|---:|---|---|---|---|
| 1 | Adobe | University Grad | Software Engineer | Frontend | San Jose, CA | 94 | $120,000-$160,000 | apply_today | [Apply](https://example.com/adobe) | needs_user_review |

## Watchlist Next 40

| # | Company | Title | Location | Fit | Salary | Status / note | Link |
|---:|---|---|---|---:|---|---|---|
| 11 | NVIDIA | University Grad | Software Engineer | Frontend | Santa Clara, CA | 91 | not checked | needs direct verification | [Open](https://example.com/nvidia) |
"""

        roles = parse_latest_report(markdown)

        self.assertEqual(roles[0]["title"], "University Grad | Software Engineer | Frontend")
        self.assertEqual(roles[0]["location"], "San Jose, CA")
        self.assertEqual(roles[0]["fit_score"], 94)
        self.assertEqual(roles[0]["salary"], "$120,000-$160,000")
        self.assertEqual(roles[0]["apply_url"], "https://example.com/adobe")
        self.assertEqual(roles[1]["title"], "University Grad | Software Engineer | Frontend")
        self.assertEqual(roles[1]["location"], "Santa Clara, CA")
        self.assertEqual(roles[1]["fit_score"], 91)
        self.assertEqual(roles[1]["report_status"], "needs direct verification")
        self.assertEqual(roles[1]["apply_url"], "https://example.com/nvidia")


if __name__ == "__main__":
    unittest.main()
