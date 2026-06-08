#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader


FORBIDDEN_PUBLIC_PATTERNS = (
    r"file://",
    r"/Users/",
    r"evidence-ledger",
    r"validation-report",
    r"application-packs",
    r"\.docx",
    r"\.pdf",
)

FORBIDDEN_RESUME_TEXT = (
    "Tailored for",
    "truthful emphasis",
    "transcript-backed strengths",
    "Computer Science undergraduate",
    "GPA 3.46",
    "Dept GPA",
    "Major GPA",
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_required_files(output_dir: Path, run_date: str) -> dict[str, Any]:
    required = [
        output_dir / f"{run_date}.md",
        output_dir / "latest.md",
        output_dir / "dashboard" / "index.html",
        output_dir / "dashboard" / "data" / "latest.json",
        output_dir / "dashboard" / "data" / "manifest.json",
        output_dir / "dashboard" / "data" / "runs" / f"{run_date}.json",
        output_dir / "public-dashboard" / "index.html",
        output_dir / "public-dashboard" / "data" / "latest.json",
        output_dir / "public-dashboard" / "data" / "manifest.json",
        output_dir / "public-dashboard" / "data" / "runs" / f"{run_date}.json",
    ]
    missing = [path.as_posix() for path in required if not path.exists()]
    return {
        "status": "pass" if not missing else "fail",
        "missing": missing,
    }


def check_public_privacy(public_dir: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for path in sorted(public_dir.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN_PUBLIC_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                findings.append({
                    "file": path.as_posix(),
                    "pattern": pattern,
                })
    return {
        "status": "pass" if not findings else "fail",
        "findings": findings,
    }


def check_resume_pdfs(output_dir: Path, run_date: str) -> dict[str, Any]:
    root = output_dir / "application-packs" / run_date
    pdfs = sorted(root.glob("*/Ayush-Yadav-Resume-{*}.pdf"))
    failures: list[dict[str, str]] = []
    for pdf in pdfs:
        try:
            reader = PdfReader(str(pdf))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            page = reader.pages[0]
            if len(reader.pages) != 1:
                failures.append({"file": pdf.as_posix(), "reason": "not one page"})
            if abs(float(page.mediabox.width) - 612) >= 2 or abs(float(page.mediabox.height) - 792) >= 2:
                failures.append({"file": pdf.as_posix(), "reason": "not Letter size"})
            if len(text) < 3000:
                failures.append({"file": pdf.as_posix(), "reason": "too little extracted text"})
            if not text.startswith("Ayush Yadav"):
                failures.append({"file": pdf.as_posix(), "reason": "does not start with Ayush Yadav"})
            lowered = text.lower()
            for forbidden in FORBIDDEN_RESUME_TEXT:
                if forbidden.lower() in lowered:
                    failures.append({"file": pdf.as_posix(), "reason": f"forbidden text: {forbidden}"})
        except Exception as exc:  # noqa: BLE001 - audit must report any parser failure.
            failures.append({"file": pdf.as_posix(), "reason": str(exc)})
    return {
        "status": "pass" if pdfs and not failures else "fail",
        "pdf_count": len(pdfs),
        "failures": failures,
    }


def check_online_run(
    public_url: str,
    local_run_id: str,
    retries: int = 6,
    retry_delay_seconds: float = 10,
) -> dict[str, Any]:
    latest_url = public_url.rstrip("/") + "/data/latest.json"
    attempts: list[dict[str, str]] = []
    for attempt in range(1, max(1, retries) + 1):
        try:
            with urllib.request.urlopen(latest_url, timeout=10) as response:
                online = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - audit must report any network/JSON failure.
            attempts.append({"attempt": str(attempt), "reason": str(exc)})
        else:
            online_run_id = str(online.get("run_id", ""))
            attempts.append({"attempt": str(attempt), "online_run_id": online_run_id})
            result = {
                "status": "pass" if online_run_id == local_run_id else "fail",
                "url": latest_url,
                "local_run_id": local_run_id,
                "online_run_id": online_run_id,
                "attempts": attempts,
            }
            if result["status"] == "pass":
                return result
        if attempt < max(1, retries):
            time.sleep(retry_delay_seconds)
    return {
        "status": "fail",
        "url": latest_url,
        "local_run_id": local_run_id,
        "attempts": attempts,
        "reason": attempts[-1].get("reason", "online run_id did not match local run_id")
        if attempts
        else "online run_id did not match local run_id",
    }


def write_audit(output_dir: Path, audit: dict[str, Any]) -> tuple[Path, Path]:
    audit_dir = output_dir / "run-audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    run_date = audit["run_date"]
    json_path = audit_dir / f"{run_date}.json"
    md_path = audit_dir / f"{run_date}.md"
    json_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        f"# Job Automator Post-Run Audit - {run_date}",
        "",
        f"Status: {'PASS' if audit['passed'] else 'FAIL'}",
        f"Run ID: `{audit.get('run_id', '')}`",
        f"Resume PDFs checked: {audit.get('resume_pdf_count', 0)}",
        "",
        "## Checks",
    ]
    for name, check in audit["checks"].items():
        lines.append(f"- {name}: {check['status']}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit a completed job-automator run.")
    parser.add_argument("--root", default=str(project_root()))
    parser.add_argument("--run-date", default=date.today().isoformat())
    parser.add_argument("--public-url", default="https://yadava5.github.io/job-automator/")
    parser.add_argument("--skip-online", action="store_true")
    parser.add_argument("--online-retries", type=int, default=6)
    parser.add_argument("--online-retry-delay-seconds", type=float, default=10)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root)
    output_dir = root / "outputs" / "job-search"
    public_dir = output_dir / "public-dashboard"
    local_latest_path = public_dir / "data" / "latest.json"
    local_run_id = ""
    if local_latest_path.exists():
        local_run_id = str(load_json(local_latest_path).get("run_id", ""))

    checks = {
        "required_files": check_required_files(output_dir, args.run_date),
        "public_privacy": check_public_privacy(public_dir),
        "resume_pdfs": check_resume_pdfs(output_dir, args.run_date),
    }
    if not args.skip_online:
        checks["online_run"] = check_online_run(
            args.public_url,
            local_run_id,
            retries=args.online_retries,
            retry_delay_seconds=args.online_retry_delay_seconds,
        )

    passed = all(check["status"] == "pass" for check in checks.values())
    audit = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "passed": passed,
        "run_date": args.run_date,
        "run_id": local_run_id,
        "resume_pdf_count": checks["resume_pdfs"]["pdf_count"],
        "checks": checks,
    }
    json_path, md_path = write_audit(output_dir, audit)
    if passed:
        print(f"Post-run audit passed: {json_path}")
        print(f"Summary: {md_path}")
        return 0

    for name, check in checks.items():
        if check["status"] != "pass":
            if name == "public_privacy":
                print("Public dashboard contains private pattern", file=sys.stderr)
            else:
                print(f"Post-run audit failed: {name}", file=sys.stderr)
    print(f"Audit report: {json_path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
