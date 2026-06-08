from __future__ import annotations

import json
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from job_scout.config import TRANSCRIPT_PDF


COURSES: list[dict[str, Any]] = [
    {"subject": "CSE", "number": 102, "title": "Computer Science & Software Engineering", "credits": 3.0, "grade": "A", "points": 12.0},
    {"subject": "CSE", "number": 174, "title": "Fundamentals of Programming & Problem Solving", "credits": 3.0, "grade": "A", "points": 12.0},
    {"subject": "CSE", "number": 201, "title": "Intro to Software Engineering", "credits": 3.0, "grade": "A", "points": 12.0},
    {"subject": "CSE", "number": 212, "title": "Software Engineering for UI/UX", "credits": 3.0, "grade": "A", "points": 12.0},
    {"subject": "CSE", "number": 262, "title": "Technology, Ethics & Global Society", "credits": 3.0, "grade": "B", "points": 9.0},
    {"subject": "CSE", "number": 271, "title": "Object-Oriented Programming", "credits": 3.0, "grade": "C", "points": 6.0},
    {"subject": "CSE", "number": 274, "title": "Data Abstractions & Structures", "credits": 3.0, "grade": "A", "points": 12.0},
    {"subject": "CSE", "number": 278, "title": "Systems I", "credits": 3.0, "grade": "A", "points": 12.0},
    {"subject": "CSE", "number": 374, "title": "Algorithms I", "credits": 3.0, "grade": "B-", "points": 8.1},
    {"subject": "CSE", "number": 381, "title": "Systems 2", "credits": 3.0, "grade": "A-", "points": 11.1},
    {"subject": "CSE", "number": 383, "title": "Web Application Programming", "credits": 3.0, "grade": "A-", "points": 11.1},
    {"subject": "CSE", "number": 385, "title": "Database Systems", "credits": 3.0, "grade": "A", "points": 12.0},
    {"subject": "CSE", "number": 432, "title": "Machine Learning", "credits": 3.0, "grade": "A+", "points": 12.0},
    {"subject": "CSE", "number": 433, "title": "Deep Learning", "credits": 3.0, "grade": "B-", "points": 8.1},
    {"subject": "CSE", "number": 443, "title": "High Performance Computing", "credits": 3.0, "grade": "A", "points": 12.0},
    {"subject": "CSE", "number": 448, "title": "Senior Design Project I", "credits": 2.0, "grade": "A", "points": 8.0},
    {"subject": "CSE", "number": 449, "title": "Senior Design Project II", "credits": 2.0, "grade": "A", "points": 8.0},
    {"subject": "CSE", "number": 465, "title": "Comparative Programming Languages", "credits": 3.0, "grade": "A-", "points": 11.1},
    {"subject": "CSE", "number": 484, "title": "Algorithms II", "credits": 3.0, "grade": "A+", "points": 12.0},
    {"subject": "STA", "number": 301, "title": "Applied Statistics", "credits": 3.0, "grade": "A-", "points": 11.1},
    {"subject": "STA", "number": 363, "title": "Intro to Statistical Modeling", "credits": 3.0, "grade": "A-", "points": 11.1},
    {"subject": "CYB", "number": 134, "title": "Introduction to Cybersecurity", "credits": 3.0, "grade": "A", "points": 12.0},
]


def compute_gpa(courses: list[dict[str, Any]]) -> float:
    credits = sum(float(course["credits"]) for course in courses)
    points = sum(float(course["points"]) for course in courses)
    return round(points / credits, 3)


def _fmt(value: float) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def build_transcript_profile() -> dict[str, Any]:
    courses = deepcopy(COURSES)
    cse_courses = [course for course in courses if course["subject"] == "CSE"]
    cse_300_plus = [course for course in cse_courses if int(course["number"]) >= 300]
    cse_400_level = [course for course in cse_courses if int(course["number"]) >= 400]
    selected_ai_data_hpc = [
        course for course in courses
        if (course["subject"], int(course["number"])) in {
            ("CSE", 385), ("CSE", 432), ("CSE", 433), ("CSE", 443),
            ("CSE", 448), ("CSE", 449), ("CSE", 484),
        }
    ]
    deans_list = ["Fall 2023", "Spring 2025", "Fall 2025"]

    return {
        "degree": {
            "school": "Miami University",
            "college": "College of Engineering & Computing",
            "degree": "B.S. in Computer Science",
            "major": "Computer Science",
            "degree_awarded": "2026-05-16",
        },
        "honors": {"deans_list": deans_list},
        "courses": courses,
        "gpa_labels": {
            "overall": "3.47",
            "cs_coursework": _fmt(compute_gpa(cse_courses)),
            "cse_300_plus": _fmt(compute_gpa(cse_300_plus)),
            "cse_400_level": _fmt(compute_gpa(cse_400_level)),
            "selected_ai_data_hpc": _fmt(compute_gpa(selected_ai_data_hpc)),
            "resume_default": "GPA: 3.47 Overall | 3.65 CS Coursework | Dean's List: Fall 2023, Spring 2025, Fall 2025",
        },
        "tailoring_groups": {
            "default": ["Database Systems", "Machine Learning", "Algorithms II", "High Performance Computing", "Software Engineering for UI/UX", "Senior Design Project I", "Senior Design Project II"],
            "ai_ml": ["Machine Learning", "Deep Learning", "Algorithms II", "Intro to Statistical Modeling", "High Performance Computing", "Database Systems"],
            "backend_platform": ["Database Systems", "Systems I", "Systems 2", "Web Application Programming", "Comparative Programming Languages", "High Performance Computing", "Algorithms II"],
            "data": ["Database Systems", "Machine Learning", "Applied Statistics", "Intro to Statistical Modeling", "Algorithms II"],
            "systems_hpc": ["High Performance Computing", "Systems I", "Systems 2", "Algorithms II", "Comparative Programming Languages"],
            "general_software": ["Data Abstractions & Structures", "Intro to Software Engineering", "Software Engineering for UI/UX", "Database Systems", "Algorithms II"],
        },
        "academic_highlights": "A+ in Machine Learning and Algorithms II; A in Database Systems and High Performance Computing",
        "evidence": {
            "source_pdf": str(TRANSCRIPT_PDF),
            "extraction_note": "Transcript PDF was read on 2026-06-04; two-column extraction was manually cross-checked for degree, GPA, Dean's List, course, and grade facts.",
        },
    }


def write_transcript_profile(path: Path) -> dict[str, Any]:
    profile = build_transcript_profile()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")
    return profile
