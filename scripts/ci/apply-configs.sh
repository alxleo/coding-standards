#!/usr/bin/env bash
# Parses skip overrides, applies configs that can't use --config paths,
# and lets consumer overrides replace our defaults for path-based configs.
#
# Required env vars: CONFIG_FILE, INPUT_SKIP
# Optional env vars: CS_ROOT (default: .coding-standards)
# Outputs: skip-hooks (via $GITHUB_OUTPUT)
set -euo pipefail

CS_ROOT="${CS_ROOT:-.coding-standards}"
CS="${CS_ROOT}/lint-configs-626465"

# ── Parse skip overrides ────────────────────────────
SKIP_FROM_OVERRIDE=""
if [ -f "$CONFIG_FILE" ]; then
  echo "Found override file: $CONFIG_FILE"
  SKIP_FROM_OVERRIDE=$(uv run --no-project python3 -c "
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

# ── Configs that don't support --config (must live at repo root) ──
copy_configs=(.shellcheckrc .editorconfig)
for cfg in "${copy_configs[@]}"; do
  if [ ! -f "$cfg" ]; then
    cp "$CS/$cfg" "$cfg"
    echo "  Copied to root: $cfg"
  else
    echo "  Kept (consumer override): $cfg"
  fi
done

# ── Path-based configs: consumer overrides replace our defaults ──
# Most tools get --config via pre-commit args. If a consumer has their
# own config at the conventional root location, overlay it into our
# config dir so the --config path still resolves to the right file.
path_configs=(
  .gitleaks.toml
  .markdownlint-cli2.yaml
  .yamllint
  .hadolint.yaml
  .jscpd.json
  .prettierrc
  commitlint.config.mjs
)
for cfg in "${path_configs[@]}"; do
  if [ -f "$cfg" ]; then
    cp "$cfg" "$CS/$cfg"
    echo "  Consumer override applied: $cfg → $CS/$cfg"
  fi
done

# Always apply pre-commit config — this IS the standard
cp "$CS/.pre-commit-config.yaml" .pre-commit-config.yaml
echo "  Applied: .pre-commit-config.yaml"

# Apply custom hook scripts (required by pre-commit local hooks)
mkdir -p scripts/hooks
if ls "${CS_ROOT}/scripts/hooks/"* &>/dev/null; then
  cp "${CS_ROOT}/scripts/hooks/"* scripts/hooks/
  chmod +x scripts/hooks/*
  echo "  Applied: scripts/hooks/*"
else
  echo "  Warning: no hook scripts found in ${CS_ROOT}/scripts/hooks/"
fi

# Verify all referenced hooks exist
for hook in scripts/hooks/*; do
  if [ ! -x "$hook" ]; then
    echo "  ERROR: hook $hook is not executable"
    exit 1
  fi
done
