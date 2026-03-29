#!/usr/bin/env bash
# Usage: lint-run.sh <logkey> <command...>
# Wraps output in a collapsed ::group::, captures to log file,
# records outcome for downstream scripts (summary, status reporting),
# and emits ::error annotations for PR inline display.
set -uo pipefail

logkey="$1"; shift
logdir="${LINT_LOG_DIR:-/tmp/lint-results}"
mkdir -p "$logdir"
logfile="${logdir}/${logkey}.log"

echo "::group::Full output"
"$@" 2>&1 | tee "$logfile"
rc=${PIPESTATUS[0]}
echo "::endgroup::"

# Record outcome for summary.sh and report-statuses.sh
if [ "$rc" -eq 0 ]; then
  echo "success" > "${logdir}/${logkey}.outcome"
else
  echo "failure" > "${logdir}/${logkey}.outcome"

  echo ""
  echo "── Failures ─────────────────────────────"
  # Show file:line errors first (most actionable), then other non-noise output
  grep -E '^\S+:[0-9]+:' "$logfile" | grep -v -E '^::' | head -20 || true
  # Show non-noise, non-banner summary (hooks that failed, error messages)
  grep -v -E '^\[INFO\]|^- Installing|^- Using|^Initializing|^- repo:|^\s*$|^::' "$logfile" \
    | grep -v -E '\.{3,}Passed' \
    | tail -20

  # Emit ::error annotations for inline PR display (max 10 per step)
  grep -E '^[^:]+:[0-9]+:[0-9]*:' "$logfile" \
    | grep -v -E '^\[INFO\]|^- |^::' \
    | head -10 \
    | while IFS= read -r line; do
        file=$(echo "$line" | cut -d: -f1)
        lineno=$(echo "$line" | cut -d: -f2)
        col=$(echo "$line" | cut -d: -f3)
        msg=$(echo "$line" | cut -d: -f4- | sed 's/^[[:space:]]*//')
        if [ -n "$file" ] && [ -n "$lineno" ] && [ -n "$msg" ]; then
          if [ -n "$col" ] && [[ "$col" =~ ^[0-9]+$ ]]; then
            echo "::error file=${file},line=${lineno},col=${col},title=${logkey}::${msg}"
          else
            echo "::error file=${file},line=${lineno},title=${logkey}::${msg}"
          fi
        fi
      done
fi
exit "$rc"
