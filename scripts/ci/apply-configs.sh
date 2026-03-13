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
  if command -v uv >/dev/null 2>&1; then
    PARSED=$(CONFIG_FILE="$CONFIG_FILE" uv run --with pyyaml --no-project python3 - <<'PYCODE' 2>/dev/null || echo '{"skip":"","overrides":{}}')
import json
import os
import pathlib
import sys

result = {"skip": "", "overrides": {}}
cfg_path = os.environ.get("CONFIG_FILE", "")
if not cfg_path or not pathlib.Path(cfg_path).is_file():
    print(json.dumps(result))
    sys.exit(0)

try:
    import yaml  # type: ignore
except Exception:
    print(json.dumps(result))
    sys.exit(0)

try:
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
except Exception:
    print(json.dumps(result))
    sys.exit(0)

hooks = cfg.get("skip-hooks", [])
if isinstance(hooks, list):
    result["skip"] = ",".join(str(h) for h in hooks)
elif hooks:
    result["skip"] = str(hooks)

overrides = cfg.get("overrides", {})
if isinstance(overrides, dict):
    result["overrides"] = overrides

print(json.dumps(result))
PYCODE
  else
    PARSED=$(CONFIG_FILE="$CONFIG_FILE" python3 - <<'PYCODE' 2>/dev/null || echo '{"skip":"","overrides":{}}')
import json
import os
import pathlib
import subprocess
import sys

result = {"skip": "", "overrides": {}}
cfg_path = os.environ.get("CONFIG_FILE", "")
if not cfg_path or not pathlib.Path(cfg_path).is_file():
    print(json.dumps(result))
    sys.exit(0)

def load_yaml():
    try:
        import yaml  # type: ignore
        return yaml
    except Exception:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", "pyyaml"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            import yaml  # type: ignore
            return yaml
        except Exception:
            return None

yaml = load_yaml()
if yaml is None:
    print(json.dumps(result))
    sys.exit(0)

try:
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
except Exception:
    print(json.dumps(result))
    sys.exit(0)

hooks = cfg.get("skip-hooks", [])
if isinstance(hooks, list):
    result["skip"] = ",".join(str(h) for h in hooks)
elif hooks:
    result["skip"] = str(hooks)

overrides = cfg.get("overrides", {})
if isinstance(overrides, dict):
    result["overrides"] = overrides

print(json.dumps(result))
PYCODE
  fi
fi

SKIP_FROM_OVERRIDE=$(printf '%s' "$PARSED" | jq -r '.skip // ""')

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
  printf '%s' "$PARSED" | jq -r ".overrides[\"$1\"] // \"\""
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
