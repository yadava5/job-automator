from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from job_scout.dashboard import write_dashboard
from job_scout.link_checker import verify_url
from job_scout.link_pack import STALE_STATUSES, build_application_pack
from job_scout.report_parser import parse_latest_report
from job_scout.resume_pipeline import create_tailored_resume, validate_resume_artifacts


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "role"


def _keywords(role: dict[str, Any]) -> list[str]:
    text = f"{role.get('title', '')} {role.get('report_status', '')}".lower()
    keywords = []
    for word in ("full-stack", "backend", "frontend", "python", "sql", "ai", "ml", "data", "platform", "react", "apis"):
        if word.replace("-", " ") in text or word in text:
            keywords.append(word)
    return keywords or ["software engineering", "Python", "SQL", "React", "backend services"]


def _unique_folder(application_pack_dir: Path, role: dict[str, Any], seen_slugs: dict[str, int]) -> Path:
    base_slug = _slug(f"{role['company']} {role['title']}")
    seen_slugs[base_slug] = seen_slugs.get(base_slug, 0) + 1
    slug = base_slug if seen_slugs[base_slug] == 1 else f"{base_slug}-{seen_slugs[base_slug]}"
    return application_pack_dir / slug


def _resolve_run_date(application_pack_dir: Path, run_date: str | None) -> str:
    if run_date:
        return run_date
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", application_pack_dir.name):
        return application_pack_dir.name
    return datetime.now().date().isoformat()


def _is_stale_role(role: dict[str, Any]) -> bool:
    return str(role.get("verification_status") or "").strip() in STALE_STATUSES


def _attach_resume(
    role: dict[str, Any],
    source_resume: Path,
    application_pack_dir: Path,
    seen_slugs: dict[str, int],
) -> dict[str, Any]:
    folder = _unique_folder(application_pack_dir, role, seen_slugs)
    evidence = [
        {
            "claim": f"Tailored resume for {role['company']} {role['title']}",
            "evidence_source": "original_resume_and_daily_report",
            "evidence_path": str(source_resume),
            "confidence": "verified",
        }
    ]
    artifacts = create_tailored_resume(
        source_resume,
        folder,
        {"company": role["company"], "title": role["title"], "keywords": _keywords(role)},
        evidence,
    )
    validation_report = validate_resume_artifacts(artifacts, source_resume)
    updated = {**role}
    updated["source_url"] = artifacts.evidence_path.resolve().as_uri()
    updated["validation_url"] = artifacts.validation_path.resolve().as_uri()
    updated["application_pack_url"] = folder.resolve().as_uri()
    if validation_report.get("is_valid"):
        updated["resume_pdf"] = artifacts.pdf_path.resolve().as_uri()
        updated["resume_docx"] = artifacts.docx_path.resolve().as_uri()
        updated["resume_review_status"] = "needs_user_review"
    else:
        updated["resume_pdf"] = ""
        updated["resume_docx"] = ""
        updated["resume_review_status"] = "resume_validation_blocked"
        manual_fields = list(updated.get("manual_fields") or [])
        if "resume validation blocked" not in manual_fields:
            manual_fields.append("resume validation blocked")
        updated["manual_fields"] = manual_fields
    return updated


def generate_from_report(
    markdown: str,
    source_resume: Path,
    dashboard_dir: Path,
    application_pack_dir: Path,
    limit: int = 30,
    verify_links: bool = True,
    run_date: str | None = None,
) -> dict[str, Any]:
    roles = parse_latest_report(markdown)
    processed: list[dict[str, Any]] = []
    excluded_stale: list[dict[str, Any]] = []
    seen_slugs: dict[str, int] = {}
    for role in roles:
        if len(processed) >= limit:
            break
        verified = verify_url(role) if verify_links else role
        if _is_stale_role(verified):
            excluded_stale.append(verified)
            continue
        processed.append(_attach_resume(verified, source_resume, application_pack_dir, seen_slugs))

    pack = build_application_pack(processed, limit=limit)
    pack["excluded_stale"] = excluded_stale
    pack["run_id"] = f"job-scout-dashboard-{datetime.now().strftime('%Y-%m-%dT%H%M%S')}"
    pack["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    resolved_run_date = _resolve_run_date(application_pack_dir, run_date)
    pack["run_date"] = resolved_run_date
    dashboard = write_dashboard(pack, dashboard_dir, run_date=resolved_run_date)
    return {"pack": pack, "dashboard": dashboard}
