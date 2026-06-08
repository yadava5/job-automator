from __future__ import annotations

import re
import socket
import urllib.error
import urllib.request
from typing import Any


STALE_TEXT_PATTERNS = (
    "job not found",
    "page not found",
    "the job you requested was not found",
    "unauthorized",
    "islisted\":false",
    "islisted: false",
)

FORM_TEXT_PATTERNS = (
    "apply for this job",
    "apply now",
    "submit application",
    "application form",
    "\"directapply\":true",
    "\"__autoserializationid\":\"formsubmit\"",
)

SENSITIVE_MANUAL_PATTERNS = (
    "manual",
    "sponsorship",
    "work-auth",
    "work authorization",
    "export-control",
    "export control",
    "clearance",
    "u.s. person",
    "citizenship",
    "visa",
    "transcript consent",
    "not explicitly new-grad",
)


def _plain(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower())


def _title_tokens(title: str) -> list[str]:
    words = re.findall(r"[a-z0-9+#]+", title.lower())
    return [word for word in words if len(word) >= 3 and word not in {"the", "and", "for", "new"}]


def classify_fetch_result(
    requested_url: str,
    final_url: str,
    status_code: int,
    html: str,
    expected_company: str,
    expected_title: str,
    report_status: str,
) -> dict[str, Any]:
    text = _plain(html)
    final_lower = final_url.lower()
    report_lower = report_status.lower()
    title_tokens = _title_tokens(expected_title)
    matched_tokens = sum(1 for token in title_tokens if token in text)
    has_form = any(pattern in text for pattern in FORM_TEXT_PATTERNS)
    manual = any(pattern in f"{report_lower} {text}" for pattern in SENSITIVE_MANUAL_PATTERNS)

    stale_text = any(pattern in text for pattern in STALE_TEXT_PATTERNS)
    strong_form_match = has_form and matched_tokens >= max(1, min(2, len(title_tokens)))
    if status_code >= 400 or "?error=true" in final_lower or (stale_text and not strong_form_match):
        return {
            "verification_status": "redirected_to_board_stale" if "?error=true" in final_lower else "page_not_found",
            "apply_ready": False,
            "verified_url": final_url,
            "reason": f"HTTP/status stale signal for {requested_url}",
        }

    generic_jobs_page = "<title>jobs" in text or "<title>jobs at" in text
    if generic_jobs_page and matched_tokens == 0:
        return {
            "verification_status": "redirected_to_board_stale",
            "apply_ready": False,
            "verified_url": final_url,
            "reason": "Generic jobs board without matching role title",
        }

    if manual:
        return {
            "verification_status": "direct_detail_verified_manual_review",
            "apply_ready": False,
            "verified_url": final_url,
            "reason": "Page loaded, but report or page text requires manual review",
        }

    if strong_form_match:
        return {
            "verification_status": "direct_form_verified",
            "apply_ready": True,
            "verified_url": final_url,
            "reason": "Same-run page load found title tokens and application form language",
        }

    return {
        "verification_status": "direct_detail_verified_manual_review",
        "apply_ready": False,
        "verified_url": final_url,
        "reason": "Page loaded but form/title confidence was not enough for easy apply",
    }


def verify_url(record: dict[str, Any], timeout: float = 8.0) -> dict[str, Any]:
    url = record.get("apply_url") or record.get("verified_url") or ""
    if not url:
        return {**record, "verification_status": "not_checked_research_only", "verified_url": "", "link_check_reason": "Missing URL"}

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(300_000)
            html = raw.decode(response.headers.get_content_charset() or "utf-8", "ignore")
            result = classify_fetch_result(
                requested_url=url,
                final_url=response.geturl(),
                status_code=response.status,
                html=html,
                expected_company=str(record.get("company", "")),
                expected_title=str(record.get("title", "")),
                report_status=str(record.get("report_status") or record.get("verification_status") or ""),
            )
    except urllib.error.HTTPError as exc:
        raw = exc.read(300_000) if exc.fp else b""
        headers = getattr(exc, "headers", None)
        charset = headers.get_content_charset() if headers and hasattr(headers, "get_content_charset") else None
        html = raw.decode(charset or "utf-8", "ignore")
        result = classify_fetch_result(
            requested_url=url,
            final_url=exc.geturl() or url,
            status_code=exc.code,
            html=html,
            expected_company=str(record.get("company", "")),
            expected_title=str(record.get("title", "")),
            report_status=str(record.get("report_status") or record.get("verification_status") or ""),
        )
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        result = {
            "verification_status": "not_checked_research_only",
            "apply_ready": False,
            "verified_url": "",
            "reason": f"{type(exc).__name__}: {exc}",
        }

    updated = {**record}
    updated["verification_status"] = result["verification_status"]
    updated["verified_url"] = result.get("verified_url") or record.get("verified_url") or url
    updated["link_check_reason"] = result.get("reason", "")
    if not result.get("apply_ready") and result["verification_status"] != "redirected_to_board_stale":
        fields = list(updated.get("manual_fields") or [])
        if "link/manual review" not in fields:
            fields.append("link/manual review")
        updated["manual_fields"] = fields
    return updated
