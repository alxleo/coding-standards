#!/usr/bin/env bash
# Parses skip overrides and copies coding-standards configs to repo root.
# Called from the lint workflow's "Apply coding-standards configs" step.
#
# Required env vars: CONFIG_FILE, INPUT_SKIP
# Outputs: skip-hooks (via $GITHUB_OUTPUT)
set -euo pipefail

# ── Parse skip overrides ────────────────────────────
SKIP_FROM_OVERRIDE=""
if [ -f "$CONFIG_FILE" ]; then
  echo "Found override file: $CONFIG_FILE"
  SKIP_FROM_OVERRIDE=$(uv run python3 -c "
import yaml, sys
try:
    with open('$CONFIG_FILE') as f:
        cfg = yaml.safe_load(f) or {}
    hooks = cfg.get('skip-hooks', [])
    print(','.join(hooks) if isinstance(hooks, list) else str(hooks))
except Exception:
    print('')
" 2>/dev/null || echo "")
fi

SKIP=""
if [ -n "$INPUT_SKIP" ]; then
  SKIP="$INPUT_SKIP"
fi
if [ -n "$SKIP_FROM_OVERRIDE" ]; then
  if [ -n "$SKIP" ]; then
    SKIP="$SKIP,$SKIP_FROM_OVERRIDE"
  else
    SKIP="$SKIP_FROM_OVERRIDE"
  fi
fi
echo "skip-hooks=$SKIP" >> "$GITHUB_OUTPUT"
if [ -n "$SKIP" ]; then
  echo "Will skip: $SKIP"
fi

# ── Copy configs (skip if consumer has their own) ──
CS=".coding-standards/lint-configs-626465"
configs=(
  .gitleaks.toml
  .markdownlint-cli2.yaml
  .shellcheckrc
  .yamllint
  .hadolint.yaml
  .jscpd.json
  .prettierrc
  .editorconfig
  .mega-linter.yml
  commitlint.config.mjs
)
for cfg in "${configs[@]}"; do
  if [ ! -f "$cfg" ]; then
    cp "$CS/$cfg" "$cfg"
    echo "  Applied: $cfg"
  else
    echo "  Kept (consumer override): $cfg"
  fi
done

# Always apply pre-commit config — this IS the standard
cp "$CS/.pre-commit-config.yaml" .pre-commit-config.yaml
echo "  Applied: .pre-commit-config.yaml"

# Apply custom hook scripts
mkdir -p scripts/hooks
cp .coding-standards/scripts/hooks/* scripts/hooks/ 2>/dev/null || true
chmod +x scripts/hooks/* 2>/dev/null || true
echo "  Applied: scripts/hooks/*"
