#!/usr/bin/env bash
# Create symlinks declared in sync-manifest.yml (entries with symlink: true).
# Called by consumer justfile after fetch: scripts/apply-symlinks.sh .coding-standards
set -euo pipefail

standards="${1:?Usage: apply-symlinks.sh <standards-dir>}"
manifest="$standards/sync-manifest.yml"

if ! command -v yq >/dev/null 2>&1; then
    echo "ERROR: yq is required but not installed. Install: https://github.com/mikefarah/yq" >&2
    exit 1
fi

refuse_traversal() {
    if [[ "$1" == *..* ]]; then
        echo "ERROR: refusing path with traversal component: $1" >&2
        exit 1
    fi
}

# Config files: symlink from repo root to standards/configs/<file>
for file in $(yq eval '.configs | to_entries | map(select(.value.symlink == true)) | .[].key' "$manifest"); do
    refuse_traversal "$file"
    ln -sf "$standards/configs/$file" "$file"
done

# Scripts with trailing slash: directory symlinks (e.g., hooks/ → scripts/hooks).
# Symlink targets must be relative to the link's parent directory.
# Uses yq regex test() — the glob "==" operator is undocumented.
for dir in $(yq eval '.scripts | to_entries | map(select((.key | test("/$")) and .value.symlink == true)) | .[].key' "$manifest"); do
    dir="${dir%/}"  # strip trailing slash
    refuse_traversal "$dir"
    link_path="scripts/$dir"
    mkdir -p "$(dirname "$link_path")"
    ln -sfn "../$standards/scripts/$dir" "$link_path"
done
