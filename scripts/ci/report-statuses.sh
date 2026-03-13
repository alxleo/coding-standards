#!/usr/bin/env bash
# Posts per-group commit statuses to GitHub/Gitea with deep links.
# Data-driven: reads outcomes from /tmp/lint-results/*.outcome
# and group metadata from groups.conf.
#
# Required env vars: GH_TOKEN, SHA, API_URL, REPO, RUN_URL, RUN_ID
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGDIR="${LINT_LOG_DIR:-/tmp/lint-results}"

# shellcheck source=lib/common.sh
. "$SCRIPT_DIR/lib/common.sh"

# ── Resolve job URL + step numbers for deep links ─────
# Uses a temp file instead of associative array for bash 3.2 compat (macOS).
STEP_URLS_FILE=$(mktemp)
trap 'rm -f "$STEP_URLS_FILE"' EXIT

JOB_JSON=$(curl -fsS \
  -H "Authorization: token ${GH_TOKEN}" \
  "${API_URL}/repos/${REPO}/actions/runs/${RUN_ID}/jobs" 2>/dev/null) || true

if [ -n "$JOB_JSON" ]; then
  printf '%s' "$JOB_JSON" | jq -r '
    first(.jobs[] | select(.name | contains("Lint"))) // empty
    | .html_url as $job_url
    | .steps[]
    | select(.number and $job_url)
    | "\(.name)\t\($job_url)#step:\(.number):1"
  ' > "$STEP_URLS_FILE" 2>/dev/null || true
fi

get_step_url() {
  local step_name="$1"
  grep -F "$step_name" "$STEP_URLS_FILE" 2>/dev/null | head -1 | cut -f2 || true
}

post_status() {
  local context="$1" outcome="$2" logkey="$3" step_name="$4"
  local state description target_url

  case "$outcome" in
    success)  state="success"; description="Passed" ;;
    failure)
      state="failure"
      description=$(extract_hint "$LOGDIR/${logkey}.log")
      if [ -z "$description" ]; then description="Failed"; fi
      ;;
    *)  return 0 ;;
  esac

  target_url=$(get_step_url "$step_name")
  target_url="${target_url:-$RUN_URL}"

  # Use jq to build valid JSON — avoids breakage from newlines/special chars
  local payload
  payload=$(jq -n \
    --arg state "$state" \
    --arg context "coding-standards: ${context}" \
    --arg description "$description" \
    --arg target_url "$target_url" \
    '{state: $state, context: $context, description: $description, target_url: $target_url}')

  curl -fsS -X POST \
    -H "Authorization: token ${GH_TOKEN}" \
    -H "Content-Type: application/json" \
    "${API_URL}/repos/${REPO}/statuses/${SHA}" \
    -d "$payload" > /dev/null
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
