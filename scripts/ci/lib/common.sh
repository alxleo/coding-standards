#!/usr/bin/env bash
# Shared helpers for CI scripts.
# Source this file: . "$(dirname "$0")/lib/common.sh"

# Noise patterns to filter from lint logs
NOISE_RE='^\[INFO\]|^- Installing|^- Using|^Initializing|^- repo:|^\s*$|^::group|^::endgroup|^::'

# Extract up to N meaningful error lines from a lint log file.
# Usage: extract_errors <logfile> [limit]
extract_errors() {
  local logfile="$1"
  local limit="${2:-5}"
  [ -f "$logfile" ] || return 0
  grep -v -E "$NOISE_RE" "$logfile" \
    | grep -E '(Failed|ERROR|Error:|error:|CRITICAL|warning:|^\S+:[0-9]+:|reported issue|hook id:)' \
    | head -"$limit"
}

# Extract a single short hint line for commit status descriptions (max 140 chars).
# Usage: extract_hint <logfile>
extract_hint() {
  local logfile="$1"
  [ -f "$logfile" ] || { echo ""; return; }
  local hint=""
  hint=$(grep -m1 -E '(Failed|ERROR|Error:|error:|CRITICAL|FATAL|reported issue)' "$logfile" \
    | sed 's/^[[:space:]]*//' | head -c 140) || true
  if [ -z "$hint" ]; then
    hint=$(grep -m1 -E '^\S+:[0-9]+:' "$logfile" \
      | sed 's/^[[:space:]]*//' | head -c 140) || true
  fi
  if [ -z "$hint" ]; then
    hint=$(grep -v -E "$NOISE_RE" "$logfile" \
      | tail -1 | sed 's/^[[:space:]]*//' | head -c 140) || true
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
