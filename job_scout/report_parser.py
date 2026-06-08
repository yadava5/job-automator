from __future__ import annotations

import re
from typing import Any


LINK_RE = re.compile(r"\[(?:Apply|Open)\]\(([^)]+)\)")


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _merge_title_fragments(cells: list[str], expected_count: int, trailing_count: int) -> list[str]:
    if len(cells) <= expected_count:
        return cells
    title_parts = cells[2:-trailing_count]
    return [cells[0], cells[1], " | ".join(title_parts), *cells[-trailing_count:]]


def _url(cell: str) -> str:
    match = LINK_RE.search(cell)
    return match.group(1) if match else ""


def _fit(value: str) -> int:
    try:
        return int(float(value.strip()))
    except ValueError:
        return 0


def _verification_status(raw_status: str, section: str) -> str:
    lowered = raw_status.lower()
    if "manual_review" in lowered or "manual review" in lowered:
        return raw_status if "manual_review" in lowered else "direct_detail_verified_manual_review"
    if section == "apply" and lowered == "apply_today":
        return "not_checked_research_only"
    if "not checked" in lowered or "needs direct verification" in lowered:
        return "not_checked_research_only"
    return "direct_detail_verified_manual_review" if section == "watchlist" else raw_status


def parse_latest_report(markdown: str) -> list[dict[str, Any]]:
    section = ""
    roles: list[dict[str, Any]] = []
    for line in markdown.splitlines():
        if line.startswith("## Apply Today Top 10"):
            section = "apply"
            continue
        if line.startswith("## Watchlist Next 40"):
            section = "watchlist"
            continue
        if line.startswith("## ") and section:
            section = ""
            continue
        if section not in {"apply", "watchlist"}:
            continue
        if not line.startswith("|") or line.startswith("|---") or "| Company |" in line:
            continue

        cells = _split_row(line)
        if section == "apply" and len(cells) >= 9:
            cells = _merge_title_fragments(cells, expected_count=9, trailing_count=6)
            rank, company, title, location, fit, salary, status, link, tailoring = cells[:9]
            roles.append(
                {
                    "rank": _fit(rank),
                    "company": company,
                    "title": title,
                    "location": location,
                    "fit_score": _fit(fit),
                    "salary": salary,
                    "report_status": status,
                    "verification_status": _verification_status(status, section),
                    "apply_url": _url(link),
                    "verified_url": _url(link),
                    "tailoring_status": re.sub(r"<[^>]+>", "", tailoring),
                    "manual_fields": ["application questions"] if "manual_review" in status else [],
                    "source_url": "",
                }
            )
        elif section == "watchlist" and len(cells) >= 8:
            cells = _merge_title_fragments(cells, expected_count=8, trailing_count=5)
            rank, company, title, location, fit, salary, note, link = cells[:8]
            roles.append(
                {
                    "rank": _fit(rank),
                    "company": company,
                    "title": title,
                    "location": location,
                    "fit_score": _fit(fit),
                    "salary": salary,
                    "report_status": note,
                    "verification_status": _verification_status(note, section),
                    "apply_url": _url(link),
                    "verified_url": _url(link),
                    "tailoring_status": "not_started",
                    "manual_fields": ["manual verification"] if "manual" in note.lower() else [],
                    "source_url": "",
                }
            )
    return roles
