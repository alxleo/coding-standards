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
    curl -fsSL -H 'Accept-Encoding: gzip' "$url" | gunzip > "$dest"
    # Verify it's valid JSON with rules
    rule_count=$(python3 -c "import json; print(len(json.load(open('$dest')).get('rules',[])))")
    echo "    → $rule_count rules"
done

echo "Cached ${#RULESETS[@]} rulesets to $RULES_DIR"
