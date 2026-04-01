#!/usr/bin/env bash
# Generic generated file drift checker.
#
# Usage: check-drift.sh <generator-command> [paths-to-check...]
#
# Runs the generator, then checks if any of the specified paths changed.
# If no paths specified, checks the entire working tree.
#
# Examples:
#   check-drift.sh "python3 scripts/generate_catalog.py" catalog.json
#   check-drift.sh "just generate-routes" services/caddy/routes.conf
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: check-drift.sh <generator-command> [paths...]"
    exit 1
fi

generator="$1"
shift
paths=("$@")

echo "Running generator: $generator"
eval "$generator"

if [[ ${#paths[@]} -eq 0 ]]; then
    changed=$(git diff --name-only)
else
    changed=$(git diff --name-only -- "${paths[@]}")
fi

if [[ -n "$changed" ]]; then
    echo "ERROR: Generated files are stale:"
    echo "${changed//$'\n'/$'\n'  }"
    echo ""
    echo "Run '$generator' and commit the results."
    exit 1
fi

echo "Generated files are up to date."
