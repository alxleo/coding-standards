#!/usr/bin/env bash
# Runs all file hygiene pre-commit hooks.
# Called by lint.yml via lint-run.sh.
set -uo pipefail
rc=0
uvx pre-commit run check-yaml --all-files || rc=1
uvx pre-commit run check-json --all-files || rc=1
uvx pre-commit run check-toml --all-files || rc=1
uvx pre-commit run check-merge-conflict --all-files || rc=1
uvx pre-commit run check-added-large-files --all-files || rc=1
uvx pre-commit run detect-private-key --all-files || rc=1
uvx pre-commit run end-of-file-fixer --all-files || rc=1
uvx pre-commit run trailing-whitespace --all-files || rc=1
uvx pre-commit run check-case-conflict --all-files || rc=1
uvx pre-commit run check-executables-have-shebangs --all-files || rc=1
uvx pre-commit run check-shebang-scripts-are-executable --all-files || rc=1
exit $rc
