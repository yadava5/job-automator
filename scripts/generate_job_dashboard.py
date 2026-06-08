#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from job_scout.config import (
    APPLICATION_PACKS_DIR,
    DASHBOARD_DIR,
    LATEST_REPORT,
    NEW_RESUME_PDF,
    PUBLIC_DASHBOARD_DIR,
)
from job_scout.dashboard import write_dashboard
from job_scout.generator import generate_from_report


def default_source_resume() -> Path:
    return NEW_RESUME_PDF


def resolve_source_resume(selected_source: Path) -> Path:
    return selected_source


def default_report_path() -> Path:
    return LATEST_REPORT


def default_run_date() -> str:
    return date.today().isoformat()


def default_application_pack_dir(run_date: str) -> Path:
    return APPLICATION_PACKS_DIR / run_date


def resolve_dashboard_dirs(args: argparse.Namespace) -> tuple[Path, Path]:
    dashboard_dir = Path(args.dashboard_dir)
    public_dashboard_dir = Path(args.public_dashboard_dir)
    if not args.skip_public_dashboard and dashboard_dir.resolve() == public_dashboard_dir.resolve():
        raise ValueError("public dashboard dir must differ from private dashboard dir unless --skip-public-dashboard is set")
    return dashboard_dir, public_dashboard_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the local job-search dashboard and application pack.")
    parser.add_argument("--report", default=str(default_report_path()))
    parser.add_argument("--source-resume", default=str(default_source_resume()))
    parser.add_argument("--dashboard-dir", default=str(DASHBOARD_DIR))
    parser.add_argument("--public-dashboard-dir", default=str(PUBLIC_DASHBOARD_DIR))
    parser.add_argument("--run-date", default=default_run_date())
    parser.add_argument("--application-pack-dir", default="")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--skip-link-verify", action="store_true")
    parser.add_argument("--skip-public-dashboard", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    report_path = Path(args.report)
    requested_source_resume = Path(args.source_resume)
    source_resume = resolve_source_resume(requested_source_resume)
    try:
        dashboard_dir, public_dashboard_dir = resolve_dashboard_dirs(args)
    except ValueError as exc:
        parser.error(str(exc))
    application_pack_dir = Path(args.application_pack_dir) if args.application_pack_dir else default_application_pack_dir(args.run_date)
    result = generate_from_report(
        markdown=report_path.read_text(encoding="utf-8"),
        source_resume=source_resume,
        dashboard_dir=dashboard_dir,
        application_pack_dir=application_pack_dir,
        limit=args.limit,
        verify_links=not args.skip_link_verify,
        run_date=args.run_date,
    )
    public_dashboard = None
    if not args.skip_public_dashboard:
        public_dashboard = write_dashboard(
            result["pack"],
            public_dashboard_dir,
            run_date=args.run_date,
            public=True,
        )
    payload = {
        "dashboard": {key: str(value) for key, value in result["dashboard"].items()},
        "public_dashboard": {key: str(value) for key, value in public_dashboard.items()} if public_dashboard else None,
        "run_date": args.run_date,
        "application_pack_dir": str(application_pack_dir),
        "source_resume": str(source_resume),
        "source_resume_requested": str(requested_source_resume),
        "top_roles": len(result["pack"]["top_roles"]),
        "easy_apply": len(result["pack"]["easy_apply"]),
        "manual_review": len(result["pack"]["manual_review"]),
        "stale": len(result["pack"]["stale"]),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
