#!/usr/bin/env bash
# Pre-commit hook: quiet on success, loud on failure.
output=$(uvx pre-commit run --hook-stage pre-commit 2>&1)
status=$?
if [ "$status" -ne 0 ]; then
    echo "$output"
    echo ""
    echo "pre-commit failed"
    exit 1
fi
echo "pre-commit passed"
