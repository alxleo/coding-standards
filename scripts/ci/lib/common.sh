#!/usr/bin/env bash
# Shared helpers for CI scripts.
# Source this file: . "$(dirname "$0")/lib/common.sh"

# Noise patterns to filter from lint logs
NOISE_RE='^\[INFO\]|^- Installing|^- Using|^Initializing|^- repo:|^\s*$|^::group|^::endgroup|^::'

# Pre-commit banner lines (e.g. "Check YAML...Passed", "Shell hygiene...Failed")
BANNER_RE='\.{3,}(Passed|Failed|Skipped)'

# Extract up to N meaningful error lines from a lint log file.
# Usage: extract_errors <logfile> [limit]
extract_errors() {
  local logfile="$1"
  local limit="${2:-5}"
  [ -f "$logfile" ] || return 0
  grep -v -E "$NOISE_RE" "$logfile" \
    | grep -v -E "$BANNER_RE" \
    | grep -E '(ERROR|Error:|error:|CRITICAL|warning:|^\S+:[0-9]+:|reported issue)' \
    | head -"$limit" || true
}

# Extract a single short hint line for commit status descriptions (max 140 chars).
# Priority: file:line errors > keyword errors > last meaningful line.
# Filters out pre-commit banner lines that match generically but carry no signal.
# Usage: extract_hint <logfile>
extract_hint() {
  local logfile="$1"
  [ -f "$logfile" ] || { echo ""; return; }
  local hint=""

  # 1. Specific file:line references (most actionable)
  hint=$(grep -m1 -E '^\S+:[0-9]+:' "$logfile" \
    | grep -v -E "$BANNER_RE" \
    | sed 's/^[[:space:]]*//' | head -c 140) || true

  # 2. Keyword errors (excluding pre-commit banners)
  if [ -z "$hint" ]; then
    hint=$(grep -E '(ERROR|Error:|error:|CRITICAL|FATAL|reported issue)' "$logfile" \
      | grep -v -E "$BANNER_RE" \
      | head -1 | sed 's/^[[:space:]]*//' | head -c 140) || true
  fi

  # 3. Last meaningful line as fallback
  if [ -z "$hint" ]; then
    hint=$(grep -v -E "$NOISE_RE" "$logfile" \
      | grep -v -E "$BANNER_RE" \
      | grep -v -E '^- hook id:|^- exit code:' \
      | tail -1 | sed 's/^[[:space:]]*//' | head -c 140) || true
  fi

  # 4. If still empty, take the banner line (better than nothing)
  if [ -z "$hint" ]; then
    hint=$(grep -m1 -E "$BANNER_RE" "$logfile" \
      | sed 's/^[[:space:]]*//' | head -c 140) || true
  fi

  echo "$hint"
}

# Iterate groups.conf and call a callback for each group.
# Usage: iterate_groups <callback_function>
# Callback receives: logkey display_name status_context step_name
iterate_groups() {
  local callback="$1"
  local conf_file
  conf_file="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/groups.conf"
  while IFS='|' read -r logkey display_name status_context step_name; do
    [[ "$logkey" =~ ^#.*$ || -z "$logkey" ]] && continue
    "$callback" "$logkey" "$display_name" "$status_context" "$step_name"
  done < "$conf_file"
}
