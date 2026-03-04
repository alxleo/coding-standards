#!/usr/bin/env bash
# Pre-commit hook: compact output via compact-run.
COMPACT="$(git rev-parse --show-toplevel)/scripts/compact-run"

if [ -x "$COMPACT" ]; then
    "$COMPACT" uvx pre-commit run --hook-stage pre-commit
else
    # Fallback: quiet on success, loud on failure
    output=$(uvx pre-commit run --hook-stage pre-commit 2>&1)
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "$output"
        echo ""
        echo "pre-commit failed"
        exit "$status"
    fi
    echo "pre-commit passed"
fi
