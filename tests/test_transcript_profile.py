import json
import tempfile
import unittest
from pathlib import Path

from job_scout.config import TRANSCRIPT_PDF
from job_scout.transcript_profile import (
    COURSES,
    build_transcript_profile,
    compute_gpa,
    write_transcript_profile,
)


class TranscriptProfileTests(unittest.TestCase):
    def test_profile_contains_degree_gpa_and_deans_list(self):
        profile = build_transcript_profile()

        self.assertEqual(profile["degree"]["degree"], "B.S. in Computer Science")
        self.assertEqual(profile["degree"]["degree_awarded"], "2026-05-16")
        self.assertEqual(profile["gpa_labels"]["overall"], "3.47")
        self.assertEqual(profile["gpa_labels"]["cs_coursework"], "3.65")
        self.assertEqual(profile["gpa_labels"]["resume_default"], "GPA: 3.47 Overall | 3.65 CS Coursework | Dean's List: Fall 2023, Spring 2025, Fall 2025")
        self.assertIn("Fall 2025", profile["honors"]["deans_list"])

    def test_computed_gpa_views_match_transcript_backed_values(self):
        profile = build_transcript_profile()

        self.assertEqual(profile["gpa_labels"]["cse_300_plus"], "3.66")
        self.assertEqual(profile["gpa_labels"]["cse_400_level"], "3.75")
        self.assertEqual(profile["gpa_labels"]["selected_ai_data_hpc"], "3.80")

    def test_cse_coursework_gpa_uses_transcript_course_totals(self):
        profile = build_transcript_profile()
        cse_courses = [course for course in profile["courses"] if course["subject"] == "CSE"]

        self.assertEqual(sum(course["credits"] for course in cse_courses), 55.0)
        self.assertEqual(sum(course["points"] for course in cse_courses), 200.5)
        self.assertEqual(compute_gpa(cse_courses), 3.645)
        self.assertEqual(profile["gpa_labels"]["cs_coursework"], "3.65")

    def test_selected_ai_data_hpc_gpa_uses_intended_courses(self):
        profile = build_transcript_profile()
        selected_keys = {
            ("CSE", 385),
            ("CSE", 432),
            ("CSE", 433),
            ("CSE", 443),
            ("CSE", 448),
            ("CSE", 449),
            ("CSE", 484),
        }
        selected_courses = [
            course for course in profile["courses"]
            if (course["subject"], course["number"]) in selected_keys
        ]

        self.assertEqual(
            [(course["subject"], course["number"], course["title"]) for course in selected_courses],
            [
                ("CSE", 385, "Database Systems"),
                ("CSE", 432, "Machine Learning"),
                ("CSE", 433, "Deep Learning"),
                ("CSE", 443, "High Performance Computing"),
                ("CSE", 448, "Senior Design Project I"),
                ("CSE", 449, "Senior Design Project II"),
                ("CSE", 484, "Algorithms II"),
            ],
        )
        self.assertEqual(sum(course["credits"] for course in selected_courses), 19.0)
        self.assertEqual(sum(course["points"] for course in selected_courses), 72.1)
        self.assertEqual(compute_gpa(selected_courses), 3.795)
        self.assertEqual(profile["gpa_labels"]["selected_ai_data_hpc"], "3.80")

    def test_tailoring_groups_include_expected_courses(self):
        profile = build_transcript_profile()

        self.assertIn("Machine Learning", profile["tailoring_groups"]["ai_ml"])
        self.assertIn("Deep Learning", profile["tailoring_groups"]["ai_ml"])
        self.assertIn("Database Systems", profile["tailoring_groups"]["backend_platform"])
        self.assertIn("High Performance Computing", profile["tailoring_groups"]["systems_hpc"])

    def test_default_tailoring_group_uses_exact_course_titles(self):
        profile = build_transcript_profile()
        course_titles = {course["title"] for course in profile["courses"]}
        default_titles = profile["tailoring_groups"]["default"]

        self.assertIn("Senior Design Project I", default_titles)
        self.assertIn("Senior Design Project II", default_titles)
        self.assertNotIn("Senior Design", default_titles)
        self.assertTrue(set(default_titles).issubset(course_titles))

    def test_profile_courses_do_not_expose_mutable_global_records(self):
        original_courses = [course.copy() for course in COURSES]
        try:
            profile = build_transcript_profile()
            profile["courses"][0]["title"] = "Corrupted Course"
            profile["courses"].append({
                "subject": "CSE",
                "number": 999,
                "title": "Injected Course",
                "credits": 3.0,
                "grade": "A",
                "points": 12.0,
            })

            rebuilt = build_transcript_profile()
            self.assertEqual(rebuilt["courses"][0]["title"], "Computer Science & Software Engineering")
            self.assertEqual(len(rebuilt["courses"]), 22)
        finally:
            COURSES[:] = original_courses

    def test_write_profile_outputs_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transcript-profile.json"
            write_transcript_profile(path)
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["gpa_labels"]["overall"], "3.47")
        self.assertEqual(payload["evidence"]["source_pdf"], str(TRANSCRIPT_PDF))


if __name__ == "__main__":
    unittest.main()
