#!/usr/bin/env bash
# Parses skip overrides, applies configs, and handles consumer overrides.
#
# For tools with native extends support (yamllint, gitleaks, markdownlint,
# commitlint), consumers specify an override file in .coding-standards.yml
# that extends our baseline. For tools without extends, consumers place
# their config at the repo root for full replacement.
#
# Hook scripts run directly from .coding-standards/scripts/hooks/ — no copy.
#
# Required env vars: CONFIG_FILE, INPUT_SKIP
# Optional env vars: CS_ROOT (default: .coding-standards)
# Outputs: skip-hooks (via $GITHUB_OUTPUT)
set -euo pipefail

CS_ROOT="${CS_ROOT:-.coding-standards}"
CS="${CS_ROOT}/lint-configs-626465"

# ── Parse .coding-standards.yml ──────────────────────
# Extracts skip-hooks and per-tool override paths in one pass.
PARSED='{"skip":"","overrides":{}}'
if [ -f "$CONFIG_FILE" ]; then
  echo "Found override file: $CONFIG_FILE"
  PARSED=$(uv run --no-project python3 -c "
import yaml, json
try:
    with open('$CONFIG_FILE') as f:
        cfg = yaml.safe_load(f) or {}
    hooks = cfg.get('skip-hooks', [])
    skip = ','.join(hooks) if isinstance(hooks, list) else str(hooks)
    overrides = cfg.get('overrides', {})
    if not isinstance(overrides, dict):
        overrides = {}
    print(json.dumps({'skip': skip, 'overrides': overrides}))
except Exception:
    print(json.dumps({'skip': '', 'overrides': {}}))
" 2>/dev/null || echo '{"skip":"","overrides":{}}')
fi

SKIP_FROM_OVERRIDE=$(printf '%s' "$PARSED" | uv run --no-project python3 -c "
import json, sys; print(json.load(sys.stdin).get('skip', ''))
" 2>/dev/null || echo "")

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

# ── Helper: read override path for a tool ─────────────
get_override() {
  printf '%s' "$PARSED" | uv run --no-project python3 -c "
import json, sys; print(json.load(sys.stdin).get('overrides', {}).get('$1', ''))
" 2>/dev/null || echo ""
}

# ── Configs without --config support (must live at repo root) ──
copy_configs=(.shellcheckrc .editorconfig)
for cfg in "${copy_configs[@]}"; do
  if [ ! -f "$cfg" ]; then
    cp "$CS/$cfg" "$cfg"
    echo "  Copied to root: $cfg"
  else
    echo "  Kept (consumer override): $cfg"
  fi
done

# ── Extends-capable configs ──────────────────────────
# For tools with native extends/inherit support, consumers specify an
# override file (which extends our .baseline) in .coding-standards.yml.
# Format: tool_key|active_config|baseline_config
extends_configs=(
  "yamllint|.yamllint|.yamllint.baseline"
  "gitleaks|.gitleaks.toml|.gitleaks.baseline.toml"
  "markdownlint|.markdownlint-cli2.yaml|.markdownlint-cli2.baseline.yaml"
  "commitlint|commitlint.config.mjs|commitlint.config.baseline.mjs"
)

for entry in "${extends_configs[@]}"; do
  IFS='|' read -r tool active baseline <<< "$entry"
  override_path=$(get_override "$tool")

  if [ -n "$override_path" ] && [ -f "$override_path" ]; then
    cp "$override_path" "$CS/$active"
    echo "  Override: $tool → $override_path (extends $baseline)"
  else
    # No override — baseline IS the active config
    cp "$CS/$baseline" "$CS/$active"
  fi
done

# ── Non-extends configs: full replacement ─────────────
# If consumer has their own config at the conventional root location,
# overlay it into our config dir so the --config path resolves correctly.
replace_configs=(.hadolint.yaml .jscpd.json .prettierrc)
for cfg in "${replace_configs[@]}"; do
  if [ -f "$cfg" ]; then
    cp "$cfg" "$CS/$cfg"
    echo "  Consumer override: $cfg → $CS/$cfg"
  fi
done

# Always apply pre-commit config — this IS the standard
cp "$CS/.pre-commit-config.yaml" .pre-commit-config.yaml
echo "  Applied: .pre-commit-config.yaml"
