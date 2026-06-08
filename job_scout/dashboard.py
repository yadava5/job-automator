from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from job_scout.link_pack import BLOCKED_RESUME_REVIEW_STATUSES, EASY_APPLY_STATUSES, STALE_STATUSES


MANUAL_FIELD_LABELS = {
    "application questions": "Application questions",
    "link/manual review": "open and confirm application page",
    "manual verification": "Manual verification",
    "resume validation blocked": "Resume validation blocked",
    "sponsorship": "Sponsorship/work authorization",
}

PRIVATE_ROLE_FIELDS = {
    "application_pack_url",
    "resume_pdf",
    "resume_docx",
    "source_url",
    "evidence_url",
    "validation_url",
}

PRIVATE_FRONTEND_FIELDS = {
    "application_pack_url",
    "tailored_resume_url",
    "tailored_resume_docx_url",
    "evidence_url",
    "validation_url",
}


def _button(label: str, url: str, kind: str = "primary") -> str:
    if not url:
        return ""
    return (
        f'<a class="btn {kind}" href="{escape(url, quote=True)}" '
        f'target="_blank" rel="noreferrer">{escape(label)}</a>'
    )


def _role_key(item: dict[str, Any], run_date: str) -> str:
    parts = [
        run_date,
        str(item.get("rank", "")),
        str(item.get("company", "")),
        str(item.get("title", "")),
    ]
    return "|".join(parts)


def _decision_controls(role_key: str, label: str) -> str:
    escaped_key = escape(role_key, quote=True)
    escaped_label = escape(label, quote=True)
    return f"""
          <div class="decision-controls" data-decision-controls data-role-key="{escaped_key}" aria-label="{escaped_label}">
            <button type="button" data-decision-choice="applied">Applied</button>
            <button type="button" data-decision-choice="not_applied">Not Applied</button>
            <button type="button" data-decision-choice="link_not_working">Link Not Working</button>
          </div>
    """


def _requires_manual_review(item: dict[str, Any]) -> bool:
    resume_status = str(item.get("resume_review_status") or "").strip()
    return (
        bool(item.get("manual_fields"))
        or resume_status in BLOCKED_RESUME_REVIEW_STATUSES
    )


def _manual_text(item: dict[str, Any]) -> str:
    labels = []
    for field in item.get("manual_fields") or []:
        raw = str(field).strip()
        if not raw:
            continue
        labels.append(MANUAL_FIELD_LABELS.get(raw.lower(), raw.replace("_", " ").strip().capitalize()))
    return f"Check: {'; '.join(labels)}" if labels else ""


def _status_text(item: dict[str, Any]) -> str:
    status = str(item.get("verification_status", "")).strip()
    if status in STALE_STATUSES:
        return "Stale or removed during same-run check"
    if _requires_manual_review(item):
        return "Review required before applying"
    if status in EASY_APPLY_STATUSES:
        return "Same-run apply link verified"
    return "Needs review"


def _link_decision(item: dict[str, Any]) -> tuple[str, str, str]:
    status = str(item.get("verification_status", ""))
    if status in STALE_STATUSES:
        return "Stale Link", "ghost", "stale"
    if _requires_manual_review(item):
        return "Review Link", "secondary", "review"
    if status in EASY_APPLY_STATUSES:
        return "Open Apply Link", "primary", "open"
    return "Review Link", "secondary", "review"


def _role_card(item: dict[str, Any], run_date: str) -> str:
    manual = _manual_text(item)
    manual_html = f"<p class=\"manual\">{escape(manual)}</p>" if manual else ""
    salary = item.get("salary") or "Salary not listed"
    status = str(item.get("verification_status", ""))
    link_label, link_kind, _ = _link_decision(item)
    decision_label = f"Application decision for {item.get('company', '')} {item.get('title', '')}"
    return f"""
      <article class="role-card" data-status="{escape(status)}">
        <div class="rank">#{escape(str(item.get("rank", "")))}</div>
        <div class="role-main">
          <h3>{escape(str(item.get("company", "")))}</h3>
          <p class="title">{escape(str(item.get("title", "")))}</p>
          <p class="meta">{escape(str(item.get("location", "")))} · Fit {escape(str(item.get("fit_score", "")))} · {escape(str(salary))}</p>
          <p class="status">{escape(_status_text(item))}</p>
          {manual_html}
        </div>
        <div class="actions">
          {_decision_controls(_role_key(item, run_date), decision_label)}
          {_button(link_label, str(item.get("primary_url", "")), link_kind)}
          {_button("Pack", str(item.get("application_pack_url", "")), "secondary")}
          {_button("Resume PDF", str(item.get("resume_pdf", "")), "secondary")}
          {_button("Resume DOCX", str(item.get("resume_docx", "")), "secondary")}
          {_button("Evidence", str(item.get("source_url", "")), "ghost")}
          {_button("Validation", str(item.get("validation_url", "")), "ghost")}
        </div>
      </article>
    """


def _section(title: str, items: list[dict[str, Any]], empty: str, run_date: str) -> str:
    cards = "\n".join(_role_card(item, run_date) for item in items)
    body = cards or f'<p class="empty">{escape(empty)}</p>'
    return f"""
      <section class="lane">
        <div class="lane-head">
          <h2>{escape(title)}</h2>
          <span>{len(items)}</span>
        </div>
        {body}
      </section>
    """


def _run_summary(pack: dict[str, Any], run_date: str) -> dict[str, Any]:
    return {
        "run_date": run_date,
        "run_id": pack.get("run_id", ""),
        "generated_at": pack.get("generated_at", ""),
        "total_roles": len(pack.get("top_roles", [])),
        "open_apply": len(pack.get("easy_apply", [])),
        "manual_review": len(pack.get("manual_review", [])),
        "research": len(pack.get("research", [])),
        "stale": len(pack.get("stale", [])),
        "data_path": f"data/runs/{run_date}.json",
    }


def _load_existing_runs(runs_dir: Path) -> dict[str, dict[str, Any]]:
    return {run_date: payload for run_date, payload, _ in _load_existing_run_records(runs_dir)}


def _load_existing_run_records(runs_dir: Path) -> list[tuple[str, dict[str, Any], Path]]:
    runs: dict[str, dict[str, Any]] = {}
    records: list[tuple[str, dict[str, Any], Path]] = []
    for path in sorted(runs_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if not _is_run_pack(payload):
            continue
        run_date = path.stem
        payload = {**payload, "run_date": run_date}
        runs[run_date] = payload
        records.append((run_date, payload, path))
    return records


def _write_sanitized_existing_runs(records: list[tuple[str, dict[str, Any], Path]]) -> dict[str, dict[str, Any]]:
    sanitized_runs: dict[str, dict[str, Any]] = {}
    for run_date, payload, path in records:
        sanitized = _sanitize_pack_for_public(payload)
        sanitized["run_date"] = run_date
        sanitized_runs[run_date] = sanitized
        path.write_text(json.dumps(sanitized, indent=2, sort_keys=True), encoding="utf-8")
    return sanitized_runs


def _remove_unloaded_run_files(runs_dir: Path, records: list[tuple[str, dict[str, Any], Path]]) -> None:
    loaded_paths = {path.resolve() for _, _, path in records}
    for path in runs_dir.glob("*.json"):
        if path.resolve() not in loaded_paths:
            path.unlink()


def _is_run_pack(payload: dict[str, Any]) -> bool:
    required_keys = {"top_roles", "easy_apply", "manual_review", "research", "stale"}
    for key in required_keys:
        bucket = payload.get(key)
        if not isinstance(bucket, list):
            return False
        if any(not isinstance(item, dict) for item in bucket):
            return False
    return True


def _sanitize_role_for_public(role: dict[str, Any]) -> dict[str, Any]:
    sanitized = {**role}
    for field in PRIVATE_ROLE_FIELDS:
        sanitized[field] = ""
    return sanitized


def _sanitize_pack_for_public(pack: dict[str, Any]) -> dict[str, Any]:
    sanitized = {**pack}
    for bucket in ("top_roles", "easy_apply", "manual_review", "research", "stale", "excluded_stale"):
        if isinstance(pack.get(bucket), list):
            sanitized[bucket] = [
                _sanitize_role_for_public(item) if isinstance(item, dict) else item
                for item in pack[bucket]
            ]
    return sanitized


def _sanitize_frontend_role_for_public(role: dict[str, Any]) -> dict[str, Any]:
    sanitized = {**role}
    for field in PRIVATE_FRONTEND_FIELDS:
        sanitized[field] = ""
    return sanitized


def _frontend_role(item: dict[str, Any], run_date: str) -> dict[str, Any]:
    status = str(item.get("verification_status", ""))
    label, _, status_class = _link_decision(item)
    return {
        "role_key": _role_key(item, run_date),
        "rank": item.get("rank", ""),
        "company": item.get("company", ""),
        "title": item.get("title", ""),
        "location": item.get("location", ""),
        "fit_score": item.get("fit_score", ""),
        "salary": item.get("salary", ""),
        "status_label": label,
        "status_class": status_class,
        "status_text": _status_text(item),
        "verification_status": status,
        "manual_fields": item.get("manual_fields") or [],
        "manual_text": _manual_text(item),
        "apply_url": item.get("primary_url", ""),
        "application_pack_url": item.get("application_pack_url", ""),
        "tailored_resume_url": item.get("resume_pdf", ""),
        "tailored_resume_docx_url": item.get("resume_docx", ""),
        "evidence_url": item.get("source_url", ""),
        "validation_url": item.get("validation_url", ""),
    }


def _frontend_run_payload(pack: dict[str, Any], run_date: str, public: bool = False) -> dict[str, Any]:
    def role(item: dict[str, Any]) -> dict[str, Any]:
        frontend = _frontend_role(item, run_date)
        return _sanitize_frontend_role_for_public(frontend) if public else frontend

    return {
        "run_date": run_date,
        "run_id": pack.get("run_id", ""),
        "generated_at": pack.get("generated_at", ""),
        "summary": _run_summary(pack, run_date),
        "jobs": [role(item) for item in pack.get("top_roles", [])],
        "easy_apply": [role(item) for item in pack.get("easy_apply", [])],
        "manual_review": [role(item) for item in pack.get("manual_review", [])],
        "research": [role(item) for item in pack.get("research", [])],
        "stale": [role(item) for item in pack.get("stale", [])],
    }


def _script_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True).replace("</", "<\\/")


def _html(
    pack: dict[str, Any],
    manifest: dict[str, Any] | None = None,
    runs: dict[str, dict[str, Any]] | None = None,
) -> str:
    top_roles = pack.get("top_roles", [])
    generated_at = pack.get("generated_at") or datetime.now().isoformat(timespec="seconds")
    run_id = pack.get("run_id") or "local-dashboard"
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>Job Search Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1c252e;
      --muted: #667482;
      --line: #d8dee5;
      --panel: #ffffff;
      --canvas: #f4f7f9;
      --accent: #266c6f;
      --accent-2: #924b2f;
      --warn: #a15c00;
      --bad: #9b2c2c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--canvas);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      padding: 22px 28px 18px;
      border-bottom: 1px solid var(--line);
      background: #fff;
      position: sticky;
      top: 0;
      z-index: 2;
    }}
    h1 {{ margin: 0; font-size: 25px; letter-spacing: 0; }}
    .subhead {{ color: var(--muted); margin-top: 6px; font-size: 14px; }}
    .header-row {{
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 16px;
    }}
    .run-picker {{
      display: inline-flex;
      flex-direction: column;
      gap: 5px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }}
    .run-picker select {{
      min-height: 34px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      padding: 5px 9px;
      font: inherit;
    }}
    .tracking-tools {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .tracking-tools button {{
      min-height: 34px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      padding: 6px 9px;
      font: inherit;
      font-size: 12px;
      font-weight: 800;
      cursor: pointer;
    }}
    .tracking-tools input[type="file"] {{ display: none; }}
    main {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 22px 18px 42px;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(4, minmax(150px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
    }}
    .metric b {{ display: block; font-size: 24px; }}
    .metric span {{ color: var(--muted); font-size: 13px; }}
    .lane {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin: 14px 0;
      overflow: hidden;
    }}
    .lane-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 13px 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfd;
    }}
    .lane-head h2 {{ margin: 0; font-size: 18px; }}
    .lane-head span {{
      min-width: 30px;
      text-align: center;
      background: #e7eef0;
      color: var(--accent);
      border-radius: 999px;
      padding: 3px 9px;
      font-weight: 700;
    }}
    .role-card {{
      display: grid;
      grid-template-columns: 48px minmax(0, 1fr) auto;
      gap: 12px;
      padding: 14px 16px;
      border-top: 1px solid #edf1f4;
    }}
    .role-card:first-of-type {{ border-top: 0; }}
    .rank {{ font-weight: 800; color: var(--accent); }}
    h3 {{ margin: 0 0 3px; font-size: 17px; }}
    .title, .meta, .status, .manual {{ margin: 3px 0; }}
    .title {{ font-weight: 650; }}
    .meta {{ color: var(--muted); font-size: 13px; }}
    .status {{ color: var(--accent-2); font-size: 13px; font-weight: 700; }}
    .manual {{ color: var(--warn); font-size: 13px; }}
    .actions {{
      display: flex;
      align-items: center;
      justify-content: flex-end;
      flex-wrap: wrap;
      gap: 8px;
      max-width: 420px;
    }}
    .decision-controls {{
      display: grid;
      grid-template-columns: repeat(3, minmax(96px, 1fr));
      gap: 6px;
      width: 100%;
    }}
    .decision-controls button {{
      min-height: 32px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--muted);
      font: inherit;
      font-size: 12px;
      font-weight: 800;
      cursor: pointer;
    }}
    .decision-controls button.active {{
      border-color: var(--accent);
      background: #e7f2ef;
      color: var(--accent);
    }}
    .decision-controls button[data-decision-choice="link_not_working"].active {{
      border-color: var(--bad);
      background: #fbeeed;
      color: var(--bad);
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      min-height: 34px;
      padding: 7px 10px;
      border-radius: 6px;
      text-decoration: none;
      border: 1px solid var(--accent);
      background: var(--accent);
      color: white;
      font-size: 13px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .btn.secondary {{ background: #fff; color: var(--accent); }}
    .btn.ghost {{ background: #fff; border-color: var(--line); color: var(--muted); }}
    .empty {{ padding: 16px; color: var(--muted); margin: 0; }}
    @media (max-width: 860px) {{
      header {{ position: static; }}
      .summary {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }}
      .role-card {{ grid-template-columns: 38px minmax(0, 1fr); }}
      .actions {{ grid-column: 2; justify-content: flex-start; max-width: none; }}
      .decision-controls {{ grid-template-columns: 1fr; }}
      .header-row {{ align-items: flex-start; flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-row">
      <div>
        <h1>Top 20-30 Today</h1>
        <div class="subhead" data-run-line>Run {escape(str(run_id))} · Generated {escape(str(generated_at))} · Apply links shown here must be same-run verified.</div>
      </div>
      <label class="run-picker">Run date
        <select id="runSelect" data-run-selector aria-label="Run date"></select>
      </label>
      <div class="tracking-tools" aria-label="Application tracking tools">
        <button type="button" data-export-decisions>Export decisions</button>
        <button type="button" class="import-decisions" data-import-decisions-trigger>Import decisions</button>
        <input type="file" accept="application/json" data-import-decisions aria-label="Import decisions file">
      </div>
    </div>
  </header>
  <main>
    <section class="summary" data-run-metrics aria-label="Run summary">
      <div class="metric"><b data-metric="total">{len(top_roles)}</b><span>Total ranked roles</span></div>
      <div class="metric"><b data-metric="easy">{len(pack.get("easy_apply", []))}</b><span>Easy apply links</span></div>
      <div class="metric"><b data-metric="manual">{len(pack.get("manual_review", []))}</b><span>Manual review</span></div>
      <div class="metric"><b data-metric="stale">{len(pack.get("stale", []))}</b><span>Stale or removed</span></div>
    </section>
    <section data-job-list>
      {_section("Easy Apply Pack", pack.get("easy_apply", []), "No same-run direct-form links passed verification yet.", str(pack.get("run_date") or ""))}
      {_section("Manual Review Pack", pack.get("manual_review", []), "No manual-review roles in this run.", str(pack.get("run_date") or ""))}
      {_section("Research Queue", pack.get("research", []), "No research-only roles in this run.", str(pack.get("run_date") or ""))}
      {_section("Stale / Removed", pack.get("stale", []), "No stale roles detected in this run.", str(pack.get("run_date") or ""))}
      {_section("All Top Roles", top_roles, "No roles available.", str(pack.get("run_date") or ""))}
    </section>
  </main>
  <script>
    window.JOB_SCOUT_MANIFEST = __MANIFEST_JSON__;
    window.JOB_SCOUT_RUNS = __RUNS_JSON__;

    const runs = window.JOB_SCOUT_RUNS || {{}};
    const selector = document.querySelector("[data-run-selector]");
    const runLine = document.querySelector("[data-run-line]");
    const jobList = document.querySelector("[data-job-list]");
    const DECISION_STORAGE_KEY = "jobScoutDecisions:v1";
    const ALLOWED_DECISIONS = new Set(["applied", "not_applied", "link_not_working"]);
    let decisions = loadDecisions();

    function escapeHtml(value) {{
      return String(value || "").replace(/[&<>"']/g, (char) => ({{
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }}[char]));
    }}

    function loadDecisions() {{
      try {{
        const parsed = JSON.parse(localStorage.getItem(DECISION_STORAGE_KEY) || "{{}}");
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {{
          return {{}};
        }}
        return sanitizeImportedDecisions(parsed);
      }} catch {{
        return {{}};
      }}
    }}

    function saveDecisions() {{
      localStorage.setItem(DECISION_STORAGE_KEY, JSON.stringify(decisions));
    }}

    function collectKnownRoleKeys() {{
      const knownRoleKeys = new Set();
      Object.values(runs).forEach((run) => {{
        if (!run || !Array.isArray(run.jobs)) {{
          return;
        }}
        run.jobs.forEach((job) => {{
          if (job && job.role_key) {{
            knownRoleKeys.add(String(job.role_key));
          }}
        }});
      }});
      return knownRoleKeys;
    }}

    function sanitizeImportedDecisions(parsed) {{
      const knownRoleKeys = collectKnownRoleKeys();
      const sanitized = {{}};
      Object.entries(parsed).forEach(([key, value]) => {{
        if (knownRoleKeys.has(key)) {{
          if (ALLOWED_DECISIONS.has(value)) {{
            sanitized[key] = value;
          }}
        }}
      }});
      return sanitized;
    }}

    function exportDecisions() {{
      const blob = new Blob([JSON.stringify(decisions, null, 2)], {{ type: "application/json" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `job-scout-decisions-${{new Date().toISOString().slice(0, 10)}}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }}

    function importDecisions(file) {{
      const reader = new FileReader();
      reader.addEventListener("load", () => {{
        try {{
          const parsed = JSON.parse(String(reader.result || "{{}}"));
          if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {{
            return;
          }}
          const imported = sanitizeImportedDecisions(parsed);
          decisions = {{ ...decisions, ...imported }};
          saveDecisions();
          applyDecisionState(document);
        }} catch {{
          return;
        }}
      }});
      reader.readAsText(file);
    }}

    function linkHtml(label, href, cssClass) {{
      if (!href) {{
        return "";
      }}
      return `<a class="${{cssClass}}" href="${{escapeHtml(href)}}" target="_blank" rel="noreferrer">${{escapeHtml(label)}}</a>`;
    }}

    function actionClass(job) {{
      if (job.status_class === "open") {{
        return "btn primary";
      }}
      if (job.status_class === "stale") {{
        return "btn ghost";
      }}
      return "btn secondary";
    }}

    function decisionControlsHtml(job) {{
      return `
        <div class="decision-controls" data-decision-controls data-role-key="${{escapeHtml(job.role_key)}}" aria-label="Application decision for ${{escapeHtml(job.company)}} ${{escapeHtml(job.title)}}">
          <button type="button" data-decision-choice="applied">Applied</button>
          <button type="button" data-decision-choice="not_applied">Not Applied</button>
          <button type="button" data-decision-choice="link_not_working">Link Not Working</button>
        </div>
      `;
    }}

    function applyDecisionState(root = document) {{
      const decisionGroups = [];
      if (root.matches && root.matches("[data-decision-controls]")) {{
        decisionGroups.push(root);
      }}
      root.querySelectorAll("[data-decision-controls]").forEach((controls) => {{
        decisionGroups.push(controls);
      }});
      decisionGroups.forEach((controls) => {{
        let value = decisions[controls.dataset.roleKey] || "not_applied";
        if (!ALLOWED_DECISIONS.has(value)) {{
          value = "not_applied";
        }}
        controls.querySelectorAll("[data-decision-choice]").forEach((button) => {{
          const active = button.dataset.decisionChoice === value;
          button.classList.toggle("active", active);
          button.setAttribute("aria-pressed", active ? "true" : "false");
        }});
      }});
    }}

    function renderRun(dateKey) {{
      const run = runs[dateKey];
      if (!run || !jobList) {{
        return;
      }}
      document.querySelector("[data-metric='total']").textContent = run.summary.total_roles;
      document.querySelector("[data-metric='easy']").textContent = run.summary.open_apply;
      document.querySelector("[data-metric='manual']").textContent = run.summary.manual_review;
      document.querySelector("[data-metric='stale']").textContent = run.summary.stale;
      if (runLine) {{
        runLine.textContent = `Run ${{run.run_id || "local-dashboard"}} · Generated ${{run.generated_at || ""}} · Apply links shown here must be same-run verified.`;
      }}
      jobList.innerHTML = run.jobs.map((job) => `
        <article class="role-card" data-status="${{escapeHtml(job.status_class)}}">
          <div class="rank">#${{escapeHtml(job.rank)}}</div>
          <div class="role-main">
            <h3>${{escapeHtml(job.company)}}</h3>
            <p class="title">${{escapeHtml(job.title)}}</p>
            <p class="meta">${{escapeHtml(job.location || "")}} · Fit ${{escapeHtml(job.fit_score)}} · ${{escapeHtml(job.salary || "Salary not listed")}}</p>
            <p class="status">${{escapeHtml(job.status_text)}}</p>
            ${{job.manual_text ? `<p class="manual">${{escapeHtml(job.manual_text)}}</p>` : ""}}
          </div>
          <div class="actions">
            ${{decisionControlsHtml(job)}}
            ${{linkHtml(job.status_label, job.apply_url, actionClass(job))}}
            ${{linkHtml("Pack", job.application_pack_url, "btn secondary")}}
            ${{linkHtml("Resume PDF", job.tailored_resume_url, "btn secondary")}}
            ${{linkHtml("Resume DOCX", job.tailored_resume_docx_url, "btn secondary")}}
            ${{linkHtml("Evidence", job.evidence_url, "btn ghost")}}
            ${{linkHtml("Validation", job.validation_url, "btn ghost")}}
          </div>
        </article>
      `).join("");
      applyDecisionState(jobList);
    }}

    document.addEventListener("click", (event) => {{
      const button = event.target.closest("[data-decision-choice]");
      if (!button) {{
        return;
      }}
      const controls = button.closest("[data-decision-controls]");
      if (!controls || !controls.dataset.roleKey) {{
        return;
      }}
      if (!ALLOWED_DECISIONS.has(button.dataset.decisionChoice)) {{
        return;
      }}
      decisions[controls.dataset.roleKey] = button.dataset.decisionChoice;
      saveDecisions();
      applyDecisionState(controls);
    }});

    document.querySelector("[data-export-decisions]")?.addEventListener("click", exportDecisions);
    document.querySelector("[data-import-decisions-trigger]")?.addEventListener("click", () => {{
      document.querySelector("[data-import-decisions]")?.click();
    }});
    document.querySelector("[data-import-decisions]")?.addEventListener("change", (event) => {{
      const file = event.target.files && event.target.files[0];
      if (file) {{
        importDecisions(file);
      }}
      event.target.value = "";
    }});

    if (selector) {{
      for (const run of window.JOB_SCOUT_MANIFEST.runs || []) {{
        const option = document.createElement("option");
        option.value = run.run_date;
        option.textContent = `${{run.run_date}} (${{run.total_roles}} roles)`;
        selector.appendChild(option);
      }}
      selector.value = window.JOB_SCOUT_MANIFEST.latest_run_date;
      selector.addEventListener("change", (event) => renderRun(event.target.value));
      renderRun(selector.value);
    }} else {{
      applyDecisionState(document);
    }}
  </script>
</body>
</html>
"""
    return (
        html.replace("__MANIFEST_JSON__", _script_json(manifest or {}))
        .replace("__RUNS_JSON__", _script_json(runs or {}))
    )


def write_dashboard(pack: dict[str, Any], output_dir: Path, run_date: str | None = None, public: bool = False) -> dict[str, Path]:
    resolved_run_date = run_date or str(pack.get("run_date") or datetime.now().date().isoformat())
    pack = {**pack, "run_date": resolved_run_date}
    if public:
        pack = _sanitize_pack_for_public(pack)
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir = output_dir / "data"
    runs_dir = data_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / "latest.json"
    manifest_path = data_dir / "manifest.json"
    run_path = runs_dir / f"{resolved_run_date}.json"
    index_path = output_dir / "index.html"
    run_path.write_text(json.dumps(pack, indent=2, sort_keys=True), encoding="utf-8")
    data_path.write_text(json.dumps(pack, indent=2, sort_keys=True), encoding="utf-8")
    if public:
        records = _load_existing_run_records(runs_dir)
        _remove_unloaded_run_files(runs_dir, records)
        runs = _write_sanitized_existing_runs(records)
    else:
        runs = _load_existing_runs(runs_dir)
    runs[resolved_run_date] = pack
    manifest = {
        "latest_run_date": resolved_run_date,
        "runs": sorted(
            (_run_summary(payload, date) for date, payload in runs.items()),
            key=lambda item: item["run_date"],
            reverse=True,
        ),
    }
    frontend_runs = {date: _frontend_run_payload(payload, date, public=public) for date, payload in runs.items()}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    index_path.write_text(_html(pack, manifest=manifest, runs=frontend_runs), encoding="utf-8")
    return {
        "index_path": index_path,
        "data_path": data_path,
        "manifest_path": manifest_path,
        "run_path": run_path,
    }
