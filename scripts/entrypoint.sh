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

# Git safe.directory — required for MegaLinter to run git commands in mounted workspaces
# (previously handled by cupcake's /entrypoint.sh)
if [[ -d "$WORKSPACE" ]]; then
  git config --global --add safe.directory "$WORKSPACE"
fi

# Config resolution (zero-config by default):
# 1. No .mega-linter.yml → use baked config directly (zero setup needed)
# 2. .mega-linter.yml with EXTENDS URL → rewrite to local path (no network)
# 3. .mega-linter.yml without EXTENDS → consumer's config takes full control
CONSUMER_CONFIG="$WORKSPACE/.mega-linter.yml"
if [[ ! -f "$CONSUMER_CONFIG" ]]; then
  # Zero-config: no consumer config → use the baked default
  export MEGALINTER_CONFIG="/opt/coding-standards/.mega-linter-default.yml"
else
  EXTENDS_URL="https://raw.githubusercontent.com/alxleo/coding-standards/main/.mega-linter-default.yml"
  if grep -q "$EXTENDS_URL" "$CONSUMER_CONFIG" 2>/dev/null; then
    # Rewrite EXTENDS URL to local path (avoids rate limits / network dependency)
    REWRITTEN_CONFIG="/tmp/.mega-linter-rewritten.yml"
    sed "s|$EXTENDS_URL|/opt/coding-standards/.mega-linter-default.yml|g" \
      "$CONSUMER_CONFIG" > "$REWRITTEN_CONFIG"
    export MEGALINTER_CONFIG="$REWRITTEN_CONFIG"
  fi
fi

# Auto-discover consumer rules and merge with baked rules.
# Consumer drops a directory → it "just works" alongside our baked rules.
#
# Semgrep: .semgrep/ in workspace → appended to REPOSITORY_SEMGREP_RULESETS
# Conftest: policy/ in workspace → already handled by REPOSITORY_CONFTEST plugin
if [[ -d "$WORKSPACE/.semgrep" ]]; then
  export REPOSITORY_SEMGREP_RULESETS="/rules/security-audit.json,/rules/trailofbits.json,/rules/custom/,$WORKSPACE/.semgrep/"
fi

case "${1:-}" in
lint)
    # Single linter: lint <name> or lint (full suite)
    # Accepts short names (ruff, shellcheck) or full IDs (PYTHON_RUFF)
    shift
    if [[ $# -gt 0 ]]; then
        ENABLE_LINTERS="$(echo "$1" | tr '[:lower:]' '[:upper:]')"
        export ENABLE_LINTERS
    fi
    exec python3 -m megalinter.run
    ;;
fix)
    export APPLY_FIXES=all
    exec python3 -m megalinter.run
    ;;
standards)
    cd "$WORKSPACE"
    python3 /opt/coding-standards/scripts/generate_repo_manifest.py
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
    python3 /opt/coding-standards/scripts/show_warnings.py
    ;;
show-config)
    cd "$WORKSPACE"
    python3 /opt/coding-standards/scripts/show_config.py . \
        --mega-linter-yml /opt/coding-standards/.mega-linter-default.yml
    ;;
blast-radius)
    cd "$WORKSPACE"
    shift
    python3 /opt/coding-standards/scripts/blast_radius.py "$@"
    ;;
help | --help | -h)
    echo "coding-standards — centralized linting image"
    echo ""
    echo "Commands:"
    echo "  (none)          Full MegaLinter suite"
    echo "  lint [LINTER]   Run all or a single linter (e.g. lint PYTHON_RUFF)"
    echo "  fix             Auto-fix all fixable issues"
    echo "  standards       Run repo-standards checks only"
    echo "  warnings        Show warnings from last run (grouped by linter)"
    echo "  show-config     Show which config file each linter uses + local overrides"
    echo "  blast-radius    Change impact analysis (blast radius, coupling, criticality)"
    echo "  catalog         Show full catalog of checks"
    echo "  help            This message"
    echo ""
    echo "Docs: https://github.com/alxleo/coding-standards/blob/main/docs/consumer-guide.md"
    ;;
*)
    # No recognized command — pass through to MegaLinter
    exec python3 -m megalinter.run "$@"
    ;;
esac
