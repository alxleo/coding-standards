# coding-standards — dev tasks for this repo.
#
# Three layers of verification:
#   just check    — fast local checks via pre-commit (~15s)
#   just lint     — full MegaLinter suite via Docker image
#   just verify   — both: check + lint + rego tests

set unstable := true

image := "coding-standards:test"
docker_args := '-v "$PWD:/tmp/lint" -e DEFAULT_WORKSPACE=/tmp/lint'

# Mount branch configs over baked configs — always test current code, not stale image

config_mounts := '-v "$PWD/lint-configs:/opt/coding-standards/configs" -v "$PWD/semgrep-rules:/opt/coding-standards/semgrep-rules" -v "$PWD/policies:/opt/coding-standards/policies" -v "$PWD/plugins:/mega-linter-plugin-custom" -v "$PWD/scripts:/opt/coding-standards/scripts" -v "$PWD/.mega-linter-default.yml:/opt/coding-standards/.mega-linter-default.yml"'
precommit_cfg := "lint-configs/.pre-commit-config.yaml"

# ── Dev workflow (use these) ───────────────────────────────

[doc('All checks — identical to CI. Pre-commit runs ruff, pytest, semgrep, catalog, etc.')]
[group('workflow')]
check:
    #!/usr/bin/env bash
    set -euo pipefail
    # Warn if branch is behind main (CI merges main, so stale branches can fail)
    if git rev-parse --git-dir > /dev/null 2>&1; then
        git fetch origin main --quiet 2>/dev/null || true
        if ! git merge-base --is-ancestor origin/main HEAD 2>/dev/null; then
            echo "⚠ Branch is behind main — merge before pushing: git merge origin/main"
        fi
    fi
    uvx pre-commit run --all-files -c {{ precommit_cfg }}

[doc('Full MegaLinter suite via Docker image (mounts branch configs)')]
[group('workflow')]
lint *LINTER:
    docker run --rm --platform linux/amd64 {{ docker_args }} {{ config_mounts }} {{ image }} lint {{ LINTER }}

[doc('Both: fast checks + full image lint + rego tests')]
[group('workflow')]
verify: check lint test-rego

# ── Image commands (via entrypoint) ──────────────────────────

[doc('Build the image locally')]
[group('image')]
build:
    docker build --platform linux/amd64 -t {{ image }} .

[doc('Auto-fix all fixable issues')]
[group('image')]
fix:
    docker run --rm --platform linux/amd64 {{ docker_args }} {{ config_mounts }} {{ image }} fix

[doc('Repo-standards checks only')]
[group('image')]
standards:
    docker run --rm --platform linux/amd64 {{ docker_args }} {{ config_mounts }} {{ image }} standards

[doc('Show warnings from last run')]
[group('image')]
warnings:
    docker run --rm --platform linux/amd64 {{ docker_args }} {{ config_mounts }} {{ image }} warnings

[doc('Show full catalog')]
[group('image')]
catalog:
    docker run --rm --platform linux/amd64 {{ docker_args }} {{ image }} catalog

# ── Individual checks ──────────────────────────────────────

[doc('Run pytest only')]
[group('check')]
test:
    uv run --with pydantic --with pyyaml --with pytest pytest test/ -v

[doc('Validate Rego policies')]
[group('check')]
test-rego:
    docker run --rm --entrypoint conftest -v "$PWD/policies:/policies" {{ image }} verify -p /policies/repo-standards/
    docker run --rm --entrypoint conftest -v "$PWD/policies:/policies" {{ image }} verify -p /policies/compose/

[doc('Validate semgrep rules')]
[group('check')]
test-semgrep:
    uvx semgrep scan --config semgrep-rules/ --validate

[doc('Regenerate catalog')]
[group('check')]
catalog-gen:
    uv run --with pydantic --with pyyaml python3 scripts/generate_catalog.py

[doc('Change impact analysis (blast radius, coupling, criticality)')]
[group('check')]
measure *ARGS:
    uv run --with networkx python3 scripts/blast_radius.py {{ ARGS }}
