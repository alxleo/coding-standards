# coding-standards — dev tasks for this repo.
#
# Three layers of verification:
#   just check    — fast local checks via pre-commit (~15s)
#   just lint     — full MegaLinter suite via Docker image
#   just verify   — both: check + lint + rego tests

set unstable := true

image := "coding-standards:test"
docker_args := '-v "$PWD:/tmp/lint" -e DEFAULT_WORKSPACE=/tmp/lint'
precommit_cfg := "lint-configs-626465/.pre-commit-config.yaml"

# ── Dev workflow (use these) ───────────────────────────────

[doc('Fast local checks — pre-commit runs all hooks including ruff, pytest, catalog drift')]
[group('workflow')]
check:
    #!/usr/bin/env bash
    [ -L .coding-standards ] || ln -s . .coding-standards
    SKIP=just-fmt-check,caddy-fmt-check,hadolint-docker uvx pre-commit run --all-files -c {{ precommit_cfg }}

[doc('Full MegaLinter suite via Docker image')]
[group('workflow')]
lint *LINTER:
    docker run --rm --platform linux/amd64 {{ docker_args }} {{ image }} lint {{ LINTER }}

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
    docker run --rm --platform linux/amd64 {{ docker_args }} {{ image }} fix

[doc('Repo-standards checks only')]
[group('image')]
standards:
    docker run --rm --platform linux/amd64 {{ docker_args }} {{ image }} standards

[doc('Show warnings from last run')]
[group('image')]
warnings:
    docker run --rm --platform linux/amd64 {{ docker_args }} {{ image }} warnings

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
    uv run --with networkx --with scipy python3 scripts/blast_radius.py {{ ARGS }}
