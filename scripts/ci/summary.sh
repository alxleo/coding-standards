#!/usr/bin/env bash
# Prints the coding-standards summary table and writes GitHub Step Summary.
#
# Required env vars:
#   HYGIENE, CRUFT, GITLEAKS, TYPOS, YAML, ACTIONS, MARKDOWN, COMMITLINT,
#   PYTHON, SHELL, JUSTFILE, JSCPD, TRIVY, SEMGREP, EXTRA
#   GITHUB_STEP_SUMMARY (set by GitHub Actions runner)
set -euo pipefail

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       coding-standards summary       ║"
echo "╠══════════════════════════════════════╣"

FAILED=0
SUMMARY_ROWS=""

report() {
  local name="$1" result="$2"
  case "$result" in
    success)
      printf "║  %-28s  %s  ║\n" "$name" "pass"
      ;;
    failure)
      printf "║  %-28s  %s  ║\n" "$name" "FAIL"
      FAILED=1
      SUMMARY_ROWS="${SUMMARY_ROWS}$(printf '| :x: FAIL | **%s** |\n' "$name")"
      ;;
    skipped)
      printf "║  %-28s  %s  ║\n" "$name" "skip"
      ;;
    *)
      printf "║  %-28s  %s  ║\n" "$name" "----"
      ;;
  esac
}

report "File hygiene"          "$HYGIENE"
report "Cruft & secret files"  "$CRUFT"
report "Secret scanning"       "$GITLEAKS"
report "Typo detection"        "$TYPOS"
report "YAML"                  "$YAML"
report "GitHub Actions"        "$ACTIONS"
report "Markdown"              "$MARKDOWN"
report "Commit messages"       "$COMMITLINT"
report "Python"                "$PYTHON"
report "Shell hygiene"         "$SHELL"
report "Justfile formatting"   "$JUSTFILE"
report "Copy-paste detection"  "$JSCPD"
report "Trivy (IaC + deps)"    "$TRIVY"
report "Semgrep (SAST)"        "$SEMGREP"
report "Extra checks"          "$EXTRA"

echo "╚══════════════════════════════════════╝"
echo ""

# Write GitHub Step Summary — only failures shown to avoid noise
{
  if [ "$FAILED" -eq 1 ]; then
    echo "### :x: coding-standards — failures detected"
    echo ""
    echo "| Status | Check |"
    echo "|--------|-------|"
    printf '%s' "$SUMMARY_ROWS"
    echo ""
    echo "> Click the failed step names in the workflow log for details."
  else
    echo "### :white_check_mark: coding-standards — all checks passed"
  fi
} >> "${GITHUB_STEP_SUMMARY:-/dev/null}"

if [ "$FAILED" -eq 1 ]; then
  echo "One or more linter groups failed. See individual steps above for details."
  exit 1
fi

echo "All checks passed."
