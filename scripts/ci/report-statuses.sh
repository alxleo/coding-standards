#!/usr/bin/env bash
# Posts per-group commit statuses to GitHub/Gitea with deep links.
#
# Required env vars:
#   GH_TOKEN, SHA, API_URL, REPO, RUN_URL, RUN_ID
#   Plus outcome vars: HYGIENE, CRUFT, GITLEAKS, TYPOS, YAML, ACTIONS,
#   MARKDOWN, COMMITLINT, PYTHON, SHELL_LINT, JUSTFILE, JSCPD, TRIVY,
#   SEMGREP, EXTRA
set -euo pipefail

# ── Resolve job URL + step numbers for deep links ─────
declare -A STEP_URLS
JOB_JSON=$(curl -fsS \
  -H "Authorization: token ${GH_TOKEN}" \
  "${API_URL}/repos/${REPO}/actions/runs/${RUN_ID}/jobs" 2>/dev/null) || true

if [ -n "$JOB_JSON" ]; then
  while IFS=$'\t' read -r step_num step_name; do
    STEP_URLS["$step_name"]="$step_num"
  done < <(printf '%s' "$JOB_JSON" | uv run python3 -c "
import json, sys
data = json.load(sys.stdin)
for job in data.get('jobs', []):
    if 'Lint' in job.get('name', ''):
        job_url = job.get('html_url', '')
        for step in job.get('steps', []):
            num = step.get('number', '')
            name = step.get('name', '')
            if job_url and num:
                print(f'{job_url}#step:{num}:1\t{name}')
        break
" 2>/dev/null) || true
fi

get_target_url() {
  local step_name="$1"
  if [ -n "${STEP_URLS[$step_name]:-}" ]; then
    echo "${STEP_URLS[$step_name]}"
  else
    echo "$RUN_URL"
  fi
}

# ── Extract first meaningful error line from lint log ──
extract_hint() {
  local logfile="/tmp/lint-results/$1.log"
  if [ ! -f "$logfile" ]; then
    echo ""
    return
  fi
  grep -m1 -E '(Failed|ERROR|Error:|error:)' "$logfile" \
    | sed 's/^[[:space:]]*//' \
    | head -c 140 || echo ""
}

post_status() {
  local context="$1" outcome="$2" logkey="$3" step_name="$4"
  local state description target_url

  case "$outcome" in
    success)  state="success"; description="Passed" ;;
    failure)
      state="failure"
      description=$(extract_hint "$logkey")
      if [ -z "$description" ]; then
        description="Failed"
      fi
      ;;
    skipped)  return 0 ;;
    *)        return 0 ;;
  esac

  target_url=$(get_target_url "$step_name")
  # Escape quotes in description for JSON
  description=$(printf '%s' "$description" | sed 's/"/\\"/g')

  curl -fsS -X POST \
    -H "Authorization: token ${GH_TOKEN}" \
    -H "Content-Type: application/json" \
    "${API_URL}/repos/${REPO}/statuses/${SHA}" \
    -d "{
      \"state\": \"${state}\",
      \"context\": \"coding-standards: ${context}\",
      \"description\": \"${description}\",
      \"target_url\": \"${target_url}\"
    }" > /dev/null
  echo "  Posted status: ${context} → ${state} (${description})"
}

post_status "file hygiene"         "$HYGIENE"     hygiene    "Lint: file hygiene"
post_status "cruft & secrets"      "$CRUFT"       cruft      "Lint: cruft & secret file blocking"
post_status "secret scanning"      "$GITLEAKS"    gitleaks   "Lint: secret scanning (gitleaks)"
post_status "typo detection"       "$TYPOS"       typos      "Lint: typo detection"
post_status "yaml"                 "$YAML"        yaml       "Lint: YAML (yamllint)"
post_status "github actions"       "$ACTIONS"     actions    "Lint: GitHub Actions (actionlint + zizmor)"
post_status "markdown"             "$MARKDOWN"    markdown   "Lint: markdown"
post_status "commit messages"      "$COMMITLINT"  commitlint "Lint: commit messages (commitlint)"
LINT_GROUP="python"
post_status "$LINT_GROUP"           "$PYTHON"      "$LINT_GROUP" "Lint: Python (ruff)"
post_status "shell hygiene"        "$SHELL_LINT"  shell      "Lint: shell hygiene"
post_status "justfile formatting"  "$JUSTFILE"    justfile   "Lint: justfile formatting"
post_status "copy-paste detection" "$JSCPD"       jscpd      "Lint: copy-paste detection (jscpd)"
post_status "trivy"                "$TRIVY"       trivy      "Security: Trivy (IaC + deps)"
post_status "semgrep"              "$SEMGREP"     semgrep    "Security: Semgrep (SAST)"
post_status "extra checks"         "$EXTRA"       extra      "Repo: extra checks"
