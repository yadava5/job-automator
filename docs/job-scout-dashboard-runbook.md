# Job Scout Dashboard Runbook

This project now has a lightweight local dashboard generator for the daily job-search automation.

## Resume Source

The default tailored-resume source is the local synced copy of the current resume PDF:

`resume/source/current/Ayush-Yadav-Resume.pdf`

Refresh it from the repo root:

```bash
python3 scripts/build_main_resume.py
```

The legacy resume source remains an external archive source and is not overwritten.

## Generate Dashboard

```bash
RUN_DATE="$(date +%F)"

python3 scripts/generate_job_dashboard.py \
  --report outputs/job-search/latest.md \
  --dashboard-dir outputs/job-search/dashboard \
  --application-pack-dir "outputs/job-search/application-packs/$RUN_DATE" \
  --run-date "$RUN_DATE" \
  --limit 30
```

Output:

- `outputs/job-search/dashboard/index.html`
- `outputs/job-search/dashboard/data/latest.json`
- `outputs/job-search/dashboard/data/manifest.json`
- `outputs/job-search/dashboard/data/runs/YYYY-MM-DD.json`
- `outputs/job-search/public-dashboard/index.html`
- `outputs/job-search/public-dashboard/data/latest.json`
- `outputs/job-search/public-dashboard/data/manifest.json`
- `outputs/job-search/public-dashboard/data/runs/YYYY-MM-DD.json`
- `outputs/job-search/application-packs/YYYY-MM-DD/<company-role>/Ayush-Yadav-Resume-{Company}.docx`
- `outputs/job-search/application-packs/YYYY-MM-DD/<company-role>/Ayush-Yadav-Resume-{Company}.pdf`
- `outputs/job-search/application-packs/YYYY-MM-DD/<company-role>/validation-report.json`
- `outputs/job-search/application-packs/YYYY-MM-DD/<company-role>/evidence-ledger.json`

`outputs/job-search/dashboard/index.html` is the stable local frontend. Dated run data is stored separately so old runs remain selectable without changing the dashboard entrypoint.

`outputs/job-search/public-dashboard/index.html` is the sanitized GitHub Pages payload. It keeps company, role, status, run-date, and apply links, but strips local packs, resumes, evidence ledgers, validation reports, and private filesystem paths.

## Publish Public Dashboard

Verify the public dashboard privacy gate without pushing:

```bash
scripts/publish_dashboard_pages.sh \
  --dashboard-dir outputs/job-search/public-dashboard \
  --verify-only
```

Publish to GitHub Pages:

```bash
scripts/publish_dashboard_pages.sh
```

The publisher uses the isolated worktree:

`tmp/job-automator-pages`

It publishes the `gh-pages` branch for:

`https://yadava5.github.io/job-automator/`

The script refuses to publish if the public dashboard contains private patterns such as `file://`, `/Users/`, `application-packs`, resume PDFs/DOCX paths, evidence ledgers, or validation reports.

## Post-Run Audit

After publishing, run the post-run audit:

```bash
RUN_DATE="$(date +%F)"
python3 scripts/post_run_audit.py --run-date "$RUN_DATE"
```

The audit writes:

- `outputs/job-search/run-audits/YYYY-MM-DD.json`
- `outputs/job-search/run-audits/YYYY-MM-DD.md`

It fails if required dashboard files are missing, if the public dashboard leaks private paths or resume/evidence files, if generated resume PDFs fail one-page/Letter/forbidden-text checks, or if the live GitHub Pages `data/latest.json` run id does not match the local public dashboard.

## Open Dashboard

```bash
scripts/open_job_dashboard.sh
```

The opener regenerates the dashboard when `outputs/job-search/latest.md` is newer than the existing HTML, then opens the local dashboard in Chrome.

It also attempts a best-effort GitHub Pages publish. If publishing fails, it still opens the local dashboard and writes details to:

`~/Library/Application Support/JobScoutDashboard/pages-publish.log`

The installed startup launcher tries `https://yadava5.github.io/job-automator/` first, then falls back to the local mirrored dashboard at `http://127.0.0.1:8787/`.

## Track Decisions

Each role has `Applied`, `Not Applied`, and `Link Not Working` controls. Decisions persist in browser `localStorage` by run date, rank, company, and title, so refreshing the page keeps your selections.

Use `Export decisions` before switching machines or browsers. Use `Import decisions` to merge a prior export back into the current dashboard. Decision export files contain company/title/date role keys, so treat them as private tracking files.

## Login Startup

To make the dashboard open when the Mac user session starts:

```bash
scripts/install_job_dashboard_launch_agent.sh
```

This installs `scripts/com.ayush.job-dashboard.plist` into `~/Library/LaunchAgents/`.

## Safety Rules

- `Open Apply Link` appears only for same-run `direct_form_verified` roles.
- Manual/sponsorship/work-authorization/export/custom-question roles show `Review Link`.
- Stale or redirected roles show `Stale Link`.
- `--skip-link-verify` is for local debugging only; normal automation runs should not use it.
- Resume outputs remain `needs_user_review`; they are generated for review and upload, not auto-submission.
- The dashboard and generated resumes never submit applications automatically.
- The legacy resume source is not overwritten.
- Public Pages publishing uses only `outputs/job-search/public-dashboard`, never `outputs/job-search/dashboard` or `outputs/job-search/application-packs`.

## Verification

Run unit tests:

```bash
python3 -m unittest discover -s tests -v
```

Verify the public publish gate:

```bash
scripts/publish_dashboard_pages.sh --verify-only
```

Verify the full post-run state:

```bash
python3 scripts/post_run_audit.py --run-date "$(date +%F)"
```

Render-check a generated PDF:

```bash
qlmanage -t -s 1400 -o tmp/render-check \
  "outputs/job-search/application-packs/$(date +%F)/<company-role>/Ayush-Yadav-Resume-{Company}.pdf"
```
