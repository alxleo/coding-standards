#!/usr/bin/env bash
# Download semgrep rulesets as JSON at Docker build time.
# Rules are bundled into the image — zero network needed at runtime.
# Refreshed on every image rebuild (weekly scheduled + every merge to main).
set -euo pipefail

RULES_DIR="${1:-/opt/coding-standards/semgrep-cached-rules}"
mkdir -p "$RULES_DIR"

# Rulesets to cache. Add new ones here.
# semgrep.dev serves JSON when Accept-Encoding: gzip is set.
declare -A RULESETS=(
    [security-audit]="https://semgrep.dev/c/p/security-audit"
    [trailofbits]="https://semgrep.dev/c/p/trailofbits"
)

for name in "${!RULESETS[@]}"; do
    url="${RULESETS[$name]}"
    dest="$RULES_DIR/${name}.json"
    echo "  Downloading $name from $url"
    curl -fsSL --compressed "$url" -o "${dest}.tmp"
    # semgrep.dev may return JSON or YAML — normalize to JSON for fast parsing
    python3 -c "
import json, sys
raw = open('${dest}.tmp').read()
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    import yaml
    data = yaml.safe_load(raw)
with open('$dest', 'w') as f:
    json.dump(data, f)
print(f'    → {len(data.get(\"rules\", []))} rules')
"
    rm -f "${dest}.tmp"
done

echo "Cached ${#RULESETS[@]} rulesets to $RULES_DIR"
