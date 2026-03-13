#!/usr/bin/env bash
# Runs cruft & secret file blocking pre-commit hooks.
# Called by lint.yml via lint-run.sh.
set -uo pipefail
rc=0
uvx pre-commit run forbid-cruft-files --all-files || rc=1
uvx pre-commit run block-secret-files --all-files || rc=1
uvx pre-commit run verify-sops-encryption --all-files || rc=1
exit $rc
