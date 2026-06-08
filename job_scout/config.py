from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_NEW_RESUME_PDF = (
    Path(os.environ["JOB_AUTOMATOR_EXTERNAL_RESUME_PDF"]).expanduser()
    if os.environ.get("JOB_AUTOMATOR_EXTERNAL_RESUME_PDF")
    else None
)
NEW_RESUME_DIR = PROJECT_ROOT / "resume/source/current"
NEW_RESUME_PDF = NEW_RESUME_DIR / "Ayush-Yadav-Resume.pdf"

ORIGINAL_RESUME_DIR = Path(
    os.environ.get("JOB_AUTOMATOR_LEGACY_RESUME_DIR", str(Path.home() / "Documents/Interview prep/Resume"))
).expanduser()
ORIGINAL_RESUME_DOCX = ORIGINAL_RESUME_DIR / "Ayush Yadav Resume (Dec 2025).docx"
ORIGINAL_RESUME_PDF = ORIGINAL_RESUME_DIR / "Ayush Yadav Resume (Dec 2025).pdf"

MAIN_RESUME_DIR = ORIGINAL_RESUME_DIR / "2026 Main Resume"
MAIN_RESUME_DOCX = MAIN_RESUME_DIR / "Ayush-Yadav-Main-Resume-2026.docx"
MAIN_RESUME_PDF = MAIN_RESUME_DIR / "Ayush-Yadav-Main-Resume-2026.pdf"
TRANSCRIPT_PDF = Path(
    os.environ.get("JOB_AUTOMATOR_TRANSCRIPT_PDF", str(Path.home() / "Downloads/Transcript_AYUSHYADAV.pdf"))
).expanduser()
TRANSCRIPT_PROFILE_JSON = MAIN_RESUME_DIR / "transcript-profile.json"
MAIN_RESUME_VALIDATION_JSON = MAIN_RESUME_DIR / "resume-validation-report.json"

JOB_SEARCH_OUTPUT_DIR = PROJECT_ROOT / "outputs/job-search"
LATEST_REPORT = JOB_SEARCH_OUTPUT_DIR / "latest.md"
DASHBOARD_DIR = JOB_SEARCH_OUTPUT_DIR / "dashboard"
PUBLIC_DASHBOARD_DIR = JOB_SEARCH_OUTPUT_DIR / "public-dashboard"
APPLICATION_PACKS_DIR = JOB_SEARCH_OUTPUT_DIR / "application-packs"

JOB_AUTOMATOR_REPO = PROJECT_ROOT
JOB_AUTOMATOR_PAGES_WORKTREE = PROJECT_ROOT / "tmp/job-automator-pages"
PUBLIC_DASHBOARD_URL = "https://yadava5.github.io/job-automator/"
