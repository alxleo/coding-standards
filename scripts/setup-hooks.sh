#!/usr/bin/env bash
# Install pre-commit hooks + custom git hook wrappers.
# Idempotent — safe to run repeatedly.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Install pre-commit framework hooks
uvx pre-commit install >/dev/null
uvx pre-commit install --hook-type commit-msg >/dev/null

# Install custom wrappers (quiet-on-success, cruft cleanup, push validation)
for hook in pre-commit commit-msg post-commit pre-push; do
    src="$REPO_ROOT/scripts/git-${hook}.sh"
    [ -f "$src" ] && cp "$src" "$REPO_ROOT/.git/hooks/$hook" && chmod +x "$REPO_ROOT/.git/hooks/$hook"
done

echo "hooks: pre-commit + commit-msg + post-commit + pre-push installed"
