#!/bin/sh
# Smart config resolution: workspace config takes precedence over baked default.
# Consumer repos just drop a .mega-linter.yml in their root — no flags needed.
if [ -f /tmp/lint/.mega-linter.yml ]; then
  export MEGALINTER_CONFIG="/tmp/lint/.mega-linter.yml"
else
  export MEGALINTER_CONFIG="/opt/coding-standards/.mega-linter.yml"
fi
exec python3 -m megalinter.run "$@"
