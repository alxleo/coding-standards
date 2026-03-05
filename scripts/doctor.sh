#!/usr/bin/env bash
# Check prerequisites for local development.
# Used by both this repo's justfile and consumer repo justfiles.
set -euo pipefail

ok=0; missing=0

check() {
    local name="$1" cmd="$2"
    if command -v "$cmd" >/dev/null 2>&1; then
        ver=$("$cmd" --version 2>&1 | head -1 | grep -oE '[0-9]+\.[0-9]+[.0-9]*' | head -1)
        printf "  ✓ %-14s %s\n" "$name" "${ver:-installed}"
        ok=$((ok + 1))
    else
        printf "  ✗ %-14s missing\n" "$name"
        missing=$((missing + 1))
    fi
}

echo "Prerequisites:"
check git git
check uv uv
check just just

# Check any extra tools passed as arguments (e.g., doctor.sh bats docker)
for cmd in "$@"; do
    check "$cmd" "$cmd"
done

echo ""
echo "Pre-commit (via uvx):"
if uvx pre-commit --version >/dev/null 2>&1; then
    ver=$(uvx pre-commit --version 2>&1 | grep -oE '[0-9]+\.[0-9]+[.0-9]*' | head -1)
    printf "  ✓ %-14s %s\n" "pre-commit" "$ver"
    ok=$((ok + 1))
else
    printf "  ✗ %-14s uvx pre-commit not working\n" "pre-commit"
    missing=$((missing + 1))
fi

echo ""
echo "$ok available, $missing missing"
[ "$missing" -eq 0 ] || exit 1
