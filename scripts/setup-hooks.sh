#!/usr/bin/env bash
# Install pre-commit hooks + custom git hook wrappers.
# Idempotent — safe to run repeatedly.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Resolve hooks directory (supports linked worktrees where .git is a file)
HOOKS_DIR="$(cd "$REPO_ROOT" && git rev-parse --git-path hooks)"
case "$HOOKS_DIR" in
    /*) ;; # already absolute
    *) HOOKS_DIR="$REPO_ROOT/$HOOKS_DIR" ;;
esac
mkdir -p "$HOOKS_DIR"

# Install pre-commit framework hooks
uvx pre-commit install >/dev/null
uvx pre-commit install --hook-type commit-msg >/dev/null

# Install custom wrappers (only for hooks pre-commit doesn't handle)
for hook in post-commit pre-push; do
    src="$REPO_ROOT/scripts/git-${hook}.sh"
    [ -f "$src" ] && cp "$src" "$HOOKS_DIR/$hook" && chmod +x "$HOOKS_DIR/$hook"
done

cat <<'EOF'
hooks installed:

  pre-commit   Lint staged files (via pre-commit)
  commit-msg   Validate conventional commit format (via pre-commit)
  post-commit  Auto-clean cruft files (.bak, .tmp, etc.)
  pre-push     Block direct push to main + full validation
EOF
