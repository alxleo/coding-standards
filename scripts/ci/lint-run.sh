#!/usr/bin/env bash
# Usage: lint-run.sh <logkey> <command...>
# Wraps output in a collapsed ::group::, captures to log file,
# and on failure shows only the meaningful error lines.
set -uo pipefail

logkey="$1"; shift
logdir="${LINT_LOG_DIR:-/tmp/lint-results}"
mkdir -p "$logdir"
logfile="${logdir}/${logkey}.log"

echo "::group::Full output"
"$@" 2>&1 | tee "$logfile"
rc=${PIPESTATUS[0]}
echo "::endgroup::"

if [ $rc -ne 0 ]; then
  echo ""
  echo "── Failures ─────────────────────────────"
  # Filter out setup noise, show everything else (hook results + errors)
  grep -v -E '^\[INFO\]|^- Installing|^- Using|^Initializing|^- repo:|^\s*$' "$logfile" \
    | tail -40
fi
exit $rc
