#!/bin/bash
# Commit-msg hook: quiet on success, loud on failure.
output=$(uvx pre-commit run --hook-stage commit-msg --commit-msg-filename "$1" 2>&1)
status=$?
if [ $status -ne 0 ]; then
    echo "$output"
    echo ""
    echo "commit-msg failed"
    exit 1
fi
echo "commit-msg passed"
