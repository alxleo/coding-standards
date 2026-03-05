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

# Config files: symlink from repo root to standards/configs/<file>
for file in $(yq eval '.configs | to_entries | map(select(.value.symlink == true)) | .[].key' "$manifest"); do
    ln -sf "$standards/configs/$file" "$file"
done

# Scripts with trailing slash: directory symlinks (e.g., hooks/ → scripts/hooks).
# Symlink targets must be relative to the link's parent directory.
for dir in $(yq eval '.scripts | to_entries | map(select(.key == "*/" and .value.symlink == true)) | .[].key' "$manifest"); do
    dir="${dir%/}"  # strip trailing slash
    link_path="scripts/$dir"
    mkdir -p "$(dirname "$link_path")"
    ln -sfn "../$standards/scripts/$dir" "$link_path"
done
