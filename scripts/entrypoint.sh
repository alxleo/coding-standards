#!/bin/sh
# Smart config resolution for coding-standards Docker image.
#
# 1. Always symlink the baked default into workspace so EXTENDS can reference it
# 2. If workspace has .mega-linter.yml, use it (can EXTENDS .coding-standards-defaults.yml)
# 3. Otherwise use the baked default directly

# Make baked config available in workspace for EXTENDS
ln -sf /opt/coding-standards/.mega-linter.yml /tmp/lint/.coding-standards-defaults.yml

if [ -f /tmp/lint/.mega-linter.yml ]; then
  export MEGALINTER_CONFIG="/tmp/lint/.mega-linter.yml"
else
  export MEGALINTER_CONFIG="/opt/coding-standards/.mega-linter.yml"
fi
exec python3 -m megalinter.run "$@"
