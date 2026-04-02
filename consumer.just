# coding-standards consumer recipes
# Setup: curl -fsSL https://raw.githubusercontent.com/alxleo/coding-standards/main/consumer.just > consumer.just
# Then:  echo 'import? "consumer.just"' >> justfile
#        just cs-init

cs-image := env("CS_IMAGE", "ghcr.io/alxleo/coding-standards:latest")
cs-repo := "https://raw.githubusercontent.com/alxleo/coding-standards/main"
cs-run := "docker run --rm -v " + justfile_directory() + ":/tmp/lint -e DEFAULT_WORKSPACE=/tmp/lint"

cs-lint *ARGS:              {{ cs-run }} {{ cs-image }} {{ ARGS }}
cs-lint-one LINTER:         {{ cs-run }} {{ cs-image }} lint {{ LINTER }}
cs-fix:                     {{ cs-run }} {{ cs-image }} fix
cs-standards:               {{ cs-run }} {{ cs-image }} standards
cs-show-config:             {{ cs-run }} {{ cs-image }} show-config
cs-catalog:                 @docker run --rm {{ cs-image }} catalog
cs-warnings:                {{ cs-run }} {{ cs-image }} warnings
cs-blast-radius *ARGS:      {{ cs-run }} {{ cs-image }} blast-radius {{ ARGS }}
cs-update:                  docker pull {{ cs-image }} && curl -fsSL {{ cs-repo }}/consumer.just -o consumer.just

# Help: renders markdown from repo (no Docker needed)
cs-help TOPIC="overview":
    @curl -fsSL {{ cs-repo }}/docs/help/{{ TOPIC }}.md 2>/dev/null || echo "Unknown topic: {{ TOPIC }}. Run: just cs-help"

# One-command setup: creates CI workflow + .gitignore (no Docker needed)
cs-init:
    #!/usr/bin/env bash
    set -euo pipefail
    REPO="{{ cs-repo }}"
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
        curl -fsSL "$REPO/templates/$TPL" > "$WORKFLOW"
        echo "✅ Created $WORKFLOW"
    fi
    curl -fsSL "$REPO/templates/gitignore-entries" | while IFS= read -r entry; do
        [ -z "$entry" ] && continue
        [[ "$entry" == \#* ]] && continue
        grep -qF "$entry" .gitignore 2>/dev/null || echo "$entry" >> .gitignore
    done
    echo "✅ .gitignore updated"
    echo ""
    echo "Next: just cs-lint"
