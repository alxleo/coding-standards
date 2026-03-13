#!/usr/bin/env bash
# Runs GitHub Actions linting hooks (actionlint + zizmor).
# Called by lint.yml via lint-run.sh.
set -uo pipefail
rc=0
uvx pre-commit run actionlint --all-files || rc=1
uvx pre-commit run zizmor --all-files || rc=1
exit $rc
