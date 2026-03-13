#!/usr/bin/env bash
# Runs Python linting hooks (ruff lint + ruff format).
# Called by lint.yml via lint-run.sh.
set -uo pipefail
rc=0
uvx pre-commit run ruff --all-files || rc=1
uvx pre-commit run ruff-format --all-files || rc=1
exit $rc
