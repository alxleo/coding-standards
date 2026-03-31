# coding-standards — dev tasks for this repo.
# Image commands: use the entrypoint (lint, fix, standards, catalog, warnings, help)
# Local checks: fast feedback without Docker

set unstable := true

image := "coding-standards:test"
docker_args := '-v "$PWD:/tmp/lint" -e DEFAULT_WORKSPACE=/tmp/lint'

# ── Image commands (via entrypoint) ──────────────────────────

[doc('Build the image locally')]
[group('image')]
build:
    docker build --platform linux/amd64 -t {{ image }} .

[doc('Full MegaLinter suite')]
[group('image')]
lint *LINTER:
    docker run --rm --platform linux/amd64 {{ docker_args }} {{ image }} lint {{ LINTER }}

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

# ── Fast local checks (no Docker) ───────────────────────────

[doc('Run fast checks locally (~15s)')]
[group('check')]
check:
    uvx ruff check --config lint-configs-626465/ruff.toml .
    uvx ruff format --check --config lint-configs-626465/ruff.toml .
    uvx pre-commit run --all-files

[doc('Run pytest')]
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
    uv run --with pydantic --with pyyaml python3 scripts/generate-catalog.py

[doc('Run all checks (fast + rego + semgrep + pytest)')]
[group('check')]
check-all: check test test-semgrep catalog-gen
