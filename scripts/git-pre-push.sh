#!/usr/bin/env bash
# Pre-push: block direct push to main, run full validation with compact output.
remote="$1"
COMPACT="$(cd "$(dirname "$0")/.." && pwd)/scripts/compact-run"
[ -x "$COMPACT" ] || COMPACT="$(git rev-parse --show-toplevel)/scripts/compact-run"

while read -r _local_ref local_sha remote_ref _remote_sha; do
    # Skip delete pushes
    if [[ "$local_sha" == "0000000000000000000000000000000000000000" ]]; then
        continue
    fi
    if [[ "$remote_ref" == "refs/heads/main" ]]; then
        echo "ERROR: Direct push to main is blocked. Create a PR instead."
        echo "  remote: $remote"
        exit 1
    fi
done

echo "Running pre-push validation..."
if [ -x "$COMPACT" ]; then
    "$COMPACT" uvx pre-commit run --all-files
else
    uvx pre-commit run --all-files
fi || {
    echo "ERROR: Pre-commit checks failed. Fix issues before pushing."
    exit 1
}
