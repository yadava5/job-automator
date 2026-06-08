#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from job_scout.config import MAIN_RESUME_DIR, ORIGINAL_RESUME_DOCX
from job_scout.main_resume import create_main_resume


def main() -> int:
    artifacts = create_main_resume(ORIGINAL_RESUME_DOCX, MAIN_RESUME_DIR)
    print(
        json.dumps(
            {
                "docx": str(artifacts.docx_path),
                "pdf": str(artifacts.pdf_path),
                "transcript_profile": str(artifacts.transcript_profile_path),
                "validation": str(artifacts.validation_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
