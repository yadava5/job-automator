from __future__ import annotations

from copy import deepcopy
from typing import Any


EASY_APPLY_STATUSES = {
    "direct_form_verified",
    "direct_apply_verified",
}

MANUAL_REVIEW_STATUSES = {
    "direct_detail_verified_manual_apply",
    "direct_detail_verified_manual_review",
    "js_only_manual_browser_required",
    "workday_manual_apply",
    "manual_review",
    "apply_today_manual_review",
    "apply_today_secondary_manual_review",
}

STALE_STATUSES = {
    "redirected_to_board_stale",
    "stale_closed",
    "stale_not_used",
    "page_not_found",
    "unauthorized",
    "is_listed_false",
}


BLOCKED_RESUME_REVIEW_STATUSES = {
    "resume_validation_blocked",
}


def _score(record: dict[str, Any]) -> float:
    try:
        return float(record.get("fit_score") or 0)
    except (TypeError, ValueError):
        return 0.0


def _normalized_item(record: dict[str, Any], rank: int) -> dict[str, Any]:
    item = deepcopy(record)
    item["rank"] = rank
    item["primary_url"] = record.get("verified_url") or record.get("apply_url") or ""
    item.setdefault("manual_fields", [])
    item.setdefault("resume_pdf", "")
    item.setdefault("resume_docx", "")
    item.setdefault("source_url", "")
    item.setdefault("validation_url", "")
    item.setdefault("salary", "")
    return item


def _requires_manual_review(item: dict[str, Any]) -> bool:
    status = str(item.get("verification_status") or "").strip()
    resume_status = str(item.get("resume_review_status") or "").strip()
    return (
        bool(item.get("manual_fields"))
        or status in MANUAL_REVIEW_STATUSES
        or resume_status in BLOCKED_RESUME_REVIEW_STATUSES
    )


def build_application_pack(records: list[dict[str, Any]], limit: int = 30) -> dict[str, Any]:
    """Split ranked roles into apply-ready, manual, research, and stale buckets."""
    ranked = sorted(records, key=_score, reverse=True)[:limit]
    top_roles = [_normalized_item(record, idx + 1) for idx, record in enumerate(ranked)]

    easy_apply: list[dict[str, Any]] = []
    manual_review: list[dict[str, Any]] = []
    research: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []

    for item in top_roles:
        status = str(item.get("verification_status") or "").strip()
        if status in STALE_STATUSES:
            stale.append(item)
        elif _requires_manual_review(item):
            manual_review.append(item)
        elif status in EASY_APPLY_STATUSES and item.get("primary_url"):
            easy_apply.append(item)
        else:
            research.append(item)

    return {
        "top_roles": top_roles,
        "easy_apply": easy_apply,
        "manual_review": manual_review,
        "research": research,
        "stale": stale,
    }
