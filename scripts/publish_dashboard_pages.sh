#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUBLIC_DASHBOARD_DIR="$ROOT/outputs/job-search/public-dashboard"
PAGES_WORKTREE="$ROOT/tmp/job-automator-pages"
REMOTE="origin"
BRANCH="gh-pages"
PUBLIC_URL="https://yadava5.github.io/job-automator/"
DRY_RUN=false
VERIFY_ONLY=false

usage() {
  cat <<'EOF'
Usage: publish_dashboard_pages.sh [options]

Options:
  --dashboard-dir PATH   Sanitized public dashboard directory to publish.
  --worktree PATH        Isolated gh-pages worktree path.
  --remote NAME          Git remote to push to. Default: origin.
  --branch NAME          Pages branch. Default: gh-pages.
  --dry-run              Verify and stage/commit locally, but do not push.
  --verify-only          Only verify the public dashboard privacy gate.
  -h, --help             Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dashboard-dir)
      PUBLIC_DASHBOARD_DIR="$2"
      shift 2
      ;;
    --worktree)
      PAGES_WORKTREE="$2"
      shift 2
      ;;
    --remote)
      REMOTE="$2"
      shift 2
      ;;
    --branch)
      BRANCH="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --verify-only)
      VERIFY_ONLY=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

FORBIDDEN_PATTERNS=(
  'file://'
  '/Users/'
  'evidence-ledger'
  'validation-report'
  'application-packs'
  '\.docx'
  '\.pdf'
)

require_public_dashboard() {
  local dir="$1"
  if [[ ! -f "$dir/index.html" ]]; then
    echo "Missing public dashboard: $dir/index.html" >&2
    exit 1
  fi
  if [[ ! -f "$dir/data/latest.json" ]]; then
    echo "Missing public dashboard data: $dir/data/latest.json" >&2
    exit 1
  fi
  if [[ ! -f "$dir/data/manifest.json" ]]; then
    echo "Missing public dashboard manifest: $dir/data/manifest.json" >&2
    exit 1
  fi
}

verify_no_private_payload() {
  local dir="$1"
  local pattern
  local grep_output
  for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
    grep_output="$(mktemp /tmp/job-automator-pages-private-grep.XXXXXX)"
    if grep -RInE --exclude-dir='.git' --exclude='.git' "$pattern" "$dir" >"$grep_output" 2>/dev/null; then
      echo "Refusing to publish private dashboard payload matching pattern: $pattern" >&2
      cat "$grep_output" >&2
      rm -f "$grep_output"
      exit 1
    fi
    rm -f "$grep_output"
  done
}

ensure_pages_worktree() {
  if [[ -d "$PAGES_WORKTREE/.git" || -f "$PAGES_WORKTREE/.git" ]]; then
    git -C "$PAGES_WORKTREE" fetch "$REMOTE" "$BRANCH" >/dev/null 2>&1 || true
    if git -C "$PAGES_WORKTREE" show-ref --verify --quiet "refs/remotes/$REMOTE/$BRANCH"; then
      git -C "$PAGES_WORKTREE" checkout -B "$BRANCH" "$REMOTE/$BRANCH"
    else
      git -C "$PAGES_WORKTREE" checkout "$BRANCH"
    fi
    if [[ "$(git -C "$PAGES_WORKTREE" branch --show-current)" != "$BRANCH" ]]; then
      echo "Refusing to publish from wrong worktree branch: $PAGES_WORKTREE" >&2
      exit 1
    fi
    git -C "$PAGES_WORKTREE" pull --ff-only "$REMOTE" "$BRANCH" >/dev/null 2>&1 || true
    return
  fi

  mkdir -p "$(dirname "$PAGES_WORKTREE")"
  git -C "$ROOT" fetch "$REMOTE" "$BRANCH" >/dev/null 2>&1 || true
  if git -C "$ROOT" show-ref --verify --quiet "refs/remotes/$REMOTE/$BRANCH"; then
    git -C "$ROOT" worktree add -B "$BRANCH" "$PAGES_WORKTREE" "$REMOTE/$BRANCH"
  else
    git -C "$ROOT" worktree add --detach "$PAGES_WORKTREE" HEAD
    git -C "$PAGES_WORKTREE" checkout --orphan "$BRANCH"
    git -C "$PAGES_WORKTREE" rm -r --quiet . >/dev/null 2>&1 || true
  fi
}

publish_dashboard() {
  ensure_pages_worktree
  rsync -a --delete --exclude '.git' "$PUBLIC_DASHBOARD_DIR"/ "$PAGES_WORKTREE"/
  touch "$PAGES_WORKTREE/.nojekyll"
  verify_no_private_payload "$PAGES_WORKTREE"

  git -C "$PAGES_WORKTREE" add -A
  if git -C "$PAGES_WORKTREE" diff --cached --quiet; then
    if [[ "$DRY_RUN" == true ]]; then
      echo "No public dashboard changes to publish."
      echo "$PUBLIC_URL"
      return
    fi
    echo "No public dashboard file changes; pushing existing branch state."
    git -C "$PAGES_WORKTREE" push "$REMOTE" "$BRANCH"
    echo "$PUBLIC_URL"
    return
  fi

  git -C "$PAGES_WORKTREE" commit -m "Publish job dashboard $(date +%F)"
  if [[ "$DRY_RUN" == true ]]; then
    echo "Dry run complete; not pushing $BRANCH."
    echo "$PUBLIC_URL"
    return
  fi

  git -C "$PAGES_WORKTREE" push "$REMOTE" "$BRANCH"
  echo "$PUBLIC_URL"
}

require_public_dashboard "$PUBLIC_DASHBOARD_DIR"
verify_no_private_payload "$PUBLIC_DASHBOARD_DIR"

if [[ "$VERIFY_ONLY" == true ]]; then
  echo "Public dashboard privacy gate passed: $PUBLIC_DASHBOARD_DIR"
  exit 0
fi

publish_dashboard
