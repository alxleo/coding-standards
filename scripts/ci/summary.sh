#!/usr/bin/env bash
# Prints the coding-standards summary table and writes GitHub Step Summary.
#
# Required env vars:
#   HYGIENE, CRUFT, GITLEAKS, TYPOS, YAML, ACTIONS, MARKDOWN, COMMITLINT,
#   PYTHON, SHELL, JUSTFILE, JSCPD, TRIVY, SEMGREP, EXTRA
#   GITHUB_STEP_SUMMARY (set by GitHub Actions runner)
set -euo pipefail

LOGDIR="/tmp/lint-results"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       coding-standards summary       ║"
echo "╠══════════════════════════════════════╣"

FAILED=0
SUMMARY_ROWS=""

# Extract the first few error lines from a lint log for inline display
extract_errors() {
  local logfile="$LOGDIR/$1.log"
  if [ ! -f "$logfile" ]; then return; fi
  # Strip setup noise, show first 5 meaningful lines
  grep -v -E '^\[INFO\]|^- Installing|^- Using|^Initializing|^- repo:|^\s*$|^::group|^::endgroup' "$logfile" \
    | grep -E '(Failed|ERROR|Error:|error:|CRITICAL|warning:|^\S+:\d+:|reported issue|hook id:)' \
    | head -5
}

report() {
  local name="$1" result="$2" logkey="${3:-}"
  case "$result" in
    success)
      printf "║  %-28s  %s  ║\n" "$name" "pass"
      ;;
    failure)
      printf "║  %-28s  %s  ║\n" "$name" "FAIL"
      FAILED=1
      # Build markdown row with error details
      local errors=""
      if [ -n "$logkey" ]; then
        errors=$(extract_errors "$logkey")
      fi
      if [ -n "$errors" ]; then
        SUMMARY_ROWS="${SUMMARY_ROWS}$(printf '| :x: FAIL | **%s** | `%s` |\n' "$name" "$(echo "$errors" | head -1 | head -c 120)")"
      else
        SUMMARY_ROWS="${SUMMARY_ROWS}$(printf '| :x: FAIL | **%s** | — |\n' "$name")"
      fi
      # Print error details in console log too
      if [ -n "$errors" ]; then
        echo "$errors" | while IFS= read -r line; do
          printf "║    ↳ %s\n" "$line"
        done
      fi
      ;;
    skipped)
      printf "║  %-28s  %s  ║\n" "$name" "skip"
      ;;
    *)
      printf "║  %-28s  %s  ║\n" "$name" "----"
      ;;
  esac
}

report "File hygiene"          "$HYGIENE"     hygiene
report "Cruft & secret files"  "$CRUFT"       cruft
report "Secret scanning"       "$GITLEAKS"    gitleaks
report "Typo detection"        "$TYPOS"       typos
report "YAML"                  "$YAML"        yaml
report "GitHub Actions"        "$ACTIONS"     actions
report "Markdown"              "$MARKDOWN"    markdown
report "Commit messages"       "$COMMITLINT"  commitlint
report "Python"                "$PYTHON"      python
report "Shell hygiene"         "$SHELL"       shell
report "Justfile formatting"   "$JUSTFILE"    justfile
report "Copy-paste detection"  "$JSCPD"       jscpd
report "Trivy (IaC + deps)"    "$TRIVY"       trivy
report "Semgrep (SAST)"        "$SEMGREP"     semgrep
report "Extra checks"          "$EXTRA"       extra

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
    # Append full error excerpts for each failed group
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
