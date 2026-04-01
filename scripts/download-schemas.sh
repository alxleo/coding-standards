#!/usr/bin/env bash
# Download schemas for v8r offline validation.
# Run at Docker build time. Schemas are bundled into the image.
set -euo pipefail

SCHEMA_DIR="${1:-/opt/coding-standards/schemas}"
mkdir -p "$SCHEMA_DIR"

declare -A SCHEMAS=(
    [github-workflow]="https://json.schemastore.org/github-workflow.json"
    [github-action]="https://json.schemastore.org/github-action.json"
    [package]="https://json.schemastore.org/package.json"
    [tsconfig]="https://json.schemastore.org/tsconfig.json"
    [docker-compose]="https://raw.githubusercontent.com/compose-spec/compose-go/main/schema/compose-spec.json"
    [prettierrc]="https://json.schemastore.org/prettierrc.json"
    [eslintrc]="https://json.schemastore.org/eslintrc.json"
    [commitlintrc]="https://json.schemastore.org/commitlintrc.json"
    [markdownlint]="https://raw.githubusercontent.com/DavidAnson/markdownlint/main/schema/markdownlint-config-schema.json"
    [yamllint]="https://json.schemastore.org/yamllint.json"
    [hadolint]="https://raw.githubusercontent.com/hadolint/hadolint/master/contrib/hadolint.json"
    [renovate]="https://docs.renovatebot.com/renovate-schema.json"
    [pre-commit]="https://json.schemastore.org/pre-commit-config.json"
    [pyproject]="https://json.schemastore.org/pyproject.json"
    [ruff]="https://json.schemastore.org/ruff.json"
    [dependabot-v2]="https://json.schemastore.org/dependabot-2.0.json"
)

# Download all schemas in parallel
pids=()
for name in "${!SCHEMAS[@]}"; do
    url="${SCHEMAS[$name]}"
    dest="$SCHEMA_DIR/${name}.json"
    curl -fsSL "$url" -o "$dest" &
    pids+=($!)
done

# Wait for all downloads and check for failures
failed=0
for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
        failed=1
    fi
done

if [[ "$failed" -ne 0 ]]; then
    echo "ERROR: Some schema downloads failed"
    exit 1
fi

echo "Downloaded ${#SCHEMAS[@]} schemas to $SCHEMA_DIR"
