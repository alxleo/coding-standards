# coding-standards consumer recipes
# Import: add `import? "consumer.just"` to your justfile
# Extract: docker run --rm ghcr.io/alxleo/coding-standards:latest cat /opt/coding-standards/consumer.just > consumer.just

cs-image := env("CS_IMAGE", "ghcr.io/alxleo/coding-standards:latest")
cs-run := "docker run --rm -v " + justfile_directory() + ":/tmp/lint -e DEFAULT_WORKSPACE=/tmp/lint"
cs-help-dir := "/opt/coding-standards/docs/help"

cs-lint *ARGS:              {{ cs-run }} {{ cs-image }} {{ ARGS }}
cs-lint-one LINTER:         {{ cs-run }} {{ cs-image }} lint {{ LINTER }}
cs-fix:                     {{ cs-run }} {{ cs-image }} fix
cs-standards:               {{ cs-run }} {{ cs-image }} standards
cs-show-config:             {{ cs-run }} {{ cs-image }} show-config
cs-catalog:                 @docker run --rm {{ cs-image }} catalog
cs-warnings:                {{ cs-run }} {{ cs-image }} warnings
cs-blast-radius *ARGS:      {{ cs-run }} {{ cs-image }} blast-radius {{ ARGS }}
cs-update:                  docker pull {{ cs-image }}

# Progressive disclosure: just cs-help, just cs-help semgrep, etc.
cs-help TOPIC="overview":
    @docker run --rm {{ cs-image }} cat {{ cs-help-dir }}/{{ TOPIC }}.md 2>/dev/null || echo "Unknown topic: {{ TOPIC }}. Run: just cs-help"

# One-command setup: creates CI workflow + .gitignore entries
cs-init:
    #!/usr/bin/env bash
    set -euo pipefail
    IMG="{{ cs-image }}"
    if [ -d .gitea ] || [ -d .gitea/workflows ]; then
        CI_DIR=".gitea/workflows"; TPL="gitea-lint.yml"
    else
        CI_DIR=".github/workflows"; TPL="github-lint.yml"
    fi
    WORKFLOW="$CI_DIR/lint.yml"
    if [ -f "$WORKFLOW" ]; then
        echo "⏭  $WORKFLOW exists"
    else
        mkdir -p "$CI_DIR"
        docker run --rm "$IMG" cat "/opt/coding-standards/templates/$TPL" > "$WORKFLOW"
        echo "✅ Created $WORKFLOW"
    fi
    docker run --rm "$IMG" cat /opt/coding-standards/templates/gitignore-entries | while IFS= read -r entry; do
        [ -z "$entry" ] && continue
        [[ "$entry" == \#* ]] && continue
        grep -qF "$entry" .gitignore 2>/dev/null || echo "$entry" >> .gitignore
    done
    echo "✅ .gitignore updated"
    echo ""
    echo "Next: just cs-lint"
