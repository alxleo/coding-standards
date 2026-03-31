#!/bin/bash
# coding-standards entrypoint — routes commands or falls through to MegaLinter.
#
# Usage:
#   docker run ... ghcr.io/alxleo/coding-standards:latest              # full lint (MegaLinter)
#   docker run ... ghcr.io/alxleo/coding-standards:latest lint PYTHON_RUFF     # single linter
#   docker run ... ghcr.io/alxleo/coding-standards:latest fix           # auto-fix all
#   docker run ... ghcr.io/alxleo/coding-standards:latest standards     # repo-standards only
#   docker run ... ghcr.io/alxleo/coding-standards:latest catalog       # show what's checked
set -euo pipefail

WORKSPACE="${DEFAULT_WORKSPACE:-/tmp/lint}"

case "${1:-}" in
    lint)
        # Single linter: lint <name> or lint (full suite)
        # Accepts short names (ruff, shellcheck) or full IDs (PYTHON_RUFF)
        shift
        if [ $# -gt 0 ]; then
            ENABLE_LINTERS="$(echo "$1" | tr '[:lower:]' '[:upper:]')"
            export ENABLE_LINTERS
        fi
        exec /entrypoint.sh
        ;;
    fix)
        export APPLY_FIXES=all
        exec /entrypoint.sh
        ;;
    standards)
        cd "$WORKSPACE"
        uv run python3 /opt/coding-standards/scripts/generate_repo_manifest.py
        conftest test repo-manifest.json \
            --all-namespaces --no-color \
            -p /opt/coding-standards/policies/repo-standards/
        rm -f repo-manifest.json
        ;;
    catalog)
        cat /opt/coding-standards/docs/catalog.md
        ;;
    warnings)
        cd "$WORKSPACE"
        uv run python3 /opt/coding-standards/scripts/show_warnings.py
        ;;
    help|--help|-h)
        echo "coding-standards — centralized linting image"
        echo ""
        echo "Commands:"
        echo "  (none)          Full MegaLinter suite"
        echo "  lint [LINTER]   Run all or a single linter (e.g. lint PYTHON_RUFF)"
        echo "  fix             Auto-fix all fixable issues"
        echo "  standards       Run repo-standards checks only"
        echo "  warnings        Show warnings from last run (grouped by linter)"
        echo "  catalog         Show full catalog of checks"
        echo "  help            This message"
        echo ""
        echo "Docs: https://github.com/alxleo/coding-standards/blob/main/docs/consumer-guide.md"
        ;;
    *)
        # No recognized command — pass through to MegaLinter
        exec /entrypoint.sh "$@"
        ;;
esac
