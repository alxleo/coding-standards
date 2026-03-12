#!/usr/bin/env bash
# Prints the coding-standards summary table and writes GitHub Step Summary.
# Data-driven: reads outcomes from /tmp/lint-results/*.outcome
# and group metadata from groups.conf.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGDIR="${LINT_LOG_DIR:-/tmp/lint-results}"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       coding-standards summary       ║"
echo "╠══════════════════════════════════════╣"

FAILED=0
SUMMARY_ROWS=""

extract_errors() {
  local logfile="$LOGDIR/$1.log"
  if [ ! -f "$logfile" ]; then return; fi
  grep -v -E '^\[INFO\]|^- Installing|^- Using|^Initializing|^- repo:|^\s*$|^::group|^::endgroup' "$logfile" \
    | grep -E '(Failed|ERROR|Error:|error:|CRITICAL|warning:|^\S+:[0-9]+:|reported issue|hook id:)' \
    | head -5
}

# ── Iterate groups from registry ──────────────────────
while IFS='|' read -r logkey display_name status_context step_name; do
  [[ "$logkey" =~ ^#.*$ || -z "$logkey" ]] && continue

  outcome_file="$LOGDIR/${logkey}.outcome"
  if [ -f "$outcome_file" ]; then
    outcome=$(cat "$outcome_file")
  else
    outcome="skipped"
  fi

  case "$outcome" in
    success)
      printf "║  %-28s  %s  ║\n" "$display_name" "pass"
      ;;
    failure)
      printf "║  %-28s  %s  ║\n" "$display_name" "FAIL"
      FAILED=1
      errors=$(extract_errors "$logkey")
      if [ -n "$errors" ]; then
        SUMMARY_ROWS="${SUMMARY_ROWS}$(printf '| :x: FAIL | **%s** | `%s` |\n' "$display_name" "$(echo "$errors" | head -1 | head -c 120)")"
        echo "$errors" | while IFS= read -r line; do
          printf "║    ↳ %s\n" "$line"
        done
      else
        SUMMARY_ROWS="${SUMMARY_ROWS}$(printf '| :x: FAIL | **%s** | — |\n' "$display_name")"
      fi
      ;;
    skipped)
      printf "║  %-28s  %s  ║\n" "$display_name" "skip"
      ;;
    *)
      printf "║  %-28s  %s  ║\n" "$display_name" "----"
      ;;
  esac
done < "$SCRIPT_DIR/groups.conf"

echo "╚══════════════════════════════════════╝"
echo ""

# Write GitHub Step Summary with error details
{
  if [ "$FAILED" -eq 1 ]; then
    echo "### :x: coding-standards — failures detected"
    echo ""
    echo "| Status | Check | Detail |"
    echo "|--------|-------|--------|"
    printf '%s' "$SUMMARY_ROWS"
    echo ""
    for logfile in "$LOGDIR"/*.log; do
      [ -f "$logfile" ] || continue
      logkey=$(basename "$logfile" .log)
      errors=$(extract_errors "$logkey")
      if [ -n "$errors" ]; then
        echo "<details><summary><b>$logkey</b> errors</summary>"
        echo ""
        echo '```'
        echo "$errors"
        echo '```'
        echo "</details>"
        echo ""
      fi
    done
  else
    echo "### :white_check_mark: coding-standards — all checks passed"
  fi
} >> "${GITHUB_STEP_SUMMARY:-/dev/null}"

if [ "$FAILED" -eq 1 ]; then
  echo "One or more linter groups failed. See details above."
  exit 1
fi

echo "All checks passed."
