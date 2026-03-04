#!/usr/bin/env bash
# Commit-msg hook: compact output via compact-run.
COMPACT="$(cd "$(dirname "$0")/.." && pwd)/scripts/compact-run"
[ -x "$COMPACT" ] || COMPACT="$(git rev-parse --show-toplevel)/scripts/compact-run"

if [ -x "$COMPACT" ]; then
    "$COMPACT" uvx pre-commit run --hook-stage commit-msg --commit-msg-filename "$1"
else
    # Fallback: quiet on success, loud on failure
    output=$(uvx pre-commit run --hook-stage commit-msg --commit-msg-filename "$1" 2>&1)
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "$output"
        echo ""
        echo "commit-msg failed"
        exit "$status"
    fi
    echo "commit-msg passed"
fi
