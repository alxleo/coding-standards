#!/usr/bin/env bash
# Posts per-group commit statuses to GitHub/Gitea with deep links.
# Data-driven: reads outcomes from /tmp/lint-results/*.outcome
# and group metadata from groups.conf.
#
# Required env vars: GH_TOKEN, SHA, API_URL, REPO, RUN_URL, RUN_ID
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGDIR="${LINT_LOG_DIR:-/tmp/lint-results}"

# ── Resolve job URL + step numbers for deep links ─────
declare -A STEP_URLS
JOB_JSON=$(curl -fsS \
  -H "Authorization: token ${GH_TOKEN}" \
  "${API_URL}/repos/${REPO}/actions/runs/${RUN_ID}/jobs" 2>/dev/null) || true

if [ -n "$JOB_JSON" ]; then
  while IFS=$'\t' read -r step_url step_name; do
    STEP_URLS["$step_name"]="$step_url"
  done < <(printf '%s' "$JOB_JSON" | uv run --no-project python3 -c "
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

# ── Extract first meaningful error line from lint log ──
extract_hint() {
  local logfile="$LOGDIR/$1.log"
  if [ ! -f "$logfile" ]; then echo ""; return; fi
  local hint=""
  hint=$(grep -m1 -E '(Failed|ERROR|Error:|error:|CRITICAL|FATAL|reported issue)' "$logfile" \
    | sed 's/^[[:space:]]*//' | head -c 140) || true
  if [ -z "$hint" ]; then
    hint=$(grep -m1 -E '^\S+:[0-9]+:' "$logfile" \
      | sed 's/^[[:space:]]*//' | head -c 140) || true
  fi
  if [ -z "$hint" ]; then
    hint=$(grep -v -E '^\[INFO\]|^- Installing|^- Using|^Initializing|^- repo:|^\s*$|^::' "$logfile" \
      | tail -1 | sed 's/^[[:space:]]*//' | head -c 140) || true
  fi
  echo "$hint"
}

post_status() {
  local context="$1" outcome="$2" logkey="$3" step_name="$4"
  local state description target_url

  case "$outcome" in
    success)  state="success"; description="Passed" ;;
    failure)
      state="failure"
      description=$(extract_hint "$logkey")
      if [ -z "$description" ]; then description="Failed"; fi
      ;;
    *)  return 0 ;;
  esac

  target_url="${STEP_URLS[$step_name]:-$RUN_URL}"
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

# ── Iterate groups from registry ──────────────────────
while IFS='|' read -r logkey display_name status_context step_name; do
  [[ "$logkey" =~ ^#.*$ || -z "$logkey" ]] && continue
  outcome_file="$LOGDIR/${logkey}.outcome"
  if [ -f "$outcome_file" ]; then
    outcome=$(cat "$outcome_file")
    post_status "$status_context" "$outcome" "$logkey" "$step_name"
  fi
done < "$SCRIPT_DIR/groups.conf"
