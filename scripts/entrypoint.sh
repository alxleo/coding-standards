#!/bin/sh
# Smart config resolution for coding-standards Docker image.
#
# 1. Detect workspace (DEFAULT_WORKSPACE, GITHUB_WORKSPACE, or /tmp/lint)
# 2. Symlink baked default into workspace so EXTENDS can reference it
# 3. If workspace has .mega-linter.yml, use it. Otherwise use baked default.

WORKSPACE="${DEFAULT_WORKSPACE:-${GITHUB_WORKSPACE:-/tmp/lint}}"

# Make baked config available in workspace for EXTENDS
ln -sf /opt/coding-standards/.mega-linter.yml "$WORKSPACE/.coding-standards-defaults.yml" 2>/dev/null || true

if [ -f "$WORKSPACE/.mega-linter.yml" ]; then
  export MEGALINTER_CONFIG="$WORKSPACE/.mega-linter.yml"
else
  export MEGALINTER_CONFIG="/opt/coding-standards/.mega-linter.yml"
fi
exec python3 -m megalinter.run "$@"
