# coding-standards — dev tasks for this repo.
#
# Three layers of verification:
#   just check    — fast local checks via pre-commit (~15s)
#   just lint     — full MegaLinter suite via Docker image
#   just verify   — both: check + lint + rego tests

set unstable

image := ""
invoke := quote(just_executable()) + " --justfile " + quote(justfile()) + ' --working-directory "$PWD"'
docker_args := '-v "$PWD:/tmp/lint" -e DEFAULT_WORKSPACE=/tmp/lint'

# Mount branch configs over baked configs — always test current code, not stale image

config_mounts := '-v "$PWD/lint-configs:/opt/coding-standards/configs" -v "$PWD/semgrep-rules:/rules/custom" -v "$PWD/policies:/opt/coding-standards/policies" -v "$PWD/plugins:/mega-linter-plugin-custom" -v "$PWD/scripts:/opt/coding-standards/scripts" -v "$PWD/.mega-linter-default.yml:/opt/coding-standards/.mega-linter-default.yml"'
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
    # Run pre-commit. If hooks auto-fix files (trailing newlines, formatting),
    # stage the fixes and re-run to verify clean. Prevents the "forgot to stage
    # the auto-fix" class of CI failures.
    if ! uvx pre-commit run --all-files -c {{ precommit_cfg }}; then
        if git diff --quiet; then
            exit 1  # genuine failure, not auto-fix
        fi
        echo ""
        echo "⚠ Hooks auto-fixed files. Staging fixes and re-checking..."
        git add -u
        uvx pre-commit run --all-files -c {{ precommit_cfg }}
    fi

[doc('Full MegaLinter suite via Docker image (mounts branch configs)')]
[group('workflow')]
[positional-arguments]
lint *LINTER:
    {{ invoke }} _with-image _run lint "$@"

[doc('Both: fast checks + full image lint + rego tests')]
[group('workflow')]
verify: check
    {{ invoke }} _with-image _verify

# ── Image commands (via entrypoint) ──────────────────────────

[doc('Check that the image builds locally and discard the build')]
[group('image')]
build:
    {{ invoke }} _with-image

[doc('Auto-fix all fixable issues')]
[group('image')]
fix:
    {{ invoke }} _with-image _run fix

[doc('Repo-standards checks only')]
[group('image')]
standards:
    {{ invoke }} _with-image _run standards

[doc('Show warnings from last run')]
[group('image')]
warnings:
    {{ invoke }} _with-image _run warnings

[doc('Show linter config sources + local overrides')]
[group('image')]
show-config:
    {{ invoke }} _with-image _run show-config

[doc('Show full catalog')]
[group('image')]
catalog:
    {{ invoke }} _with-image _catalog

# ── Individual checks ──────────────────────────────────────

[doc('Run pytest only')]
[group('check')]
test:
    uv run --with pydantic --with pyyaml --with pytest pytest test/ -v

[doc('Validate Rego policies')]
[group('check')]
test-rego:
    {{ invoke }} _with-image _test-rego

[positional-arguments]
_with-image *COMMAND:
    #!/usr/bin/env bash
    set -euo pipefail
    build_dir=$(mktemp -d "${TMPDIR:-/tmp}/coding-standards.XXXXXX")
    builder="coding-standards-${build_dir##*.}"
    tag="coding-standards:$builder"
    builder_created=false

    # The unique builder owns its cache volume and the invocation owns its image tag.
    cleanup() {
        local result=$?
        local cleanup_failed=false
        if docker image inspect "$tag" >/dev/null 2>&1; then
            docker image rm "$tag" || cleanup_failed=true
        fi
        if "$builder_created"; then
            docker buildx rm "$builder" || cleanup_failed=true
        fi
        rmdir "$build_dir" || cleanup_failed=true
        if (( result == 0 )) && "$cleanup_failed"; then
            result=1
        fi
        exit "$result"
    }
    trap cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM

    docker buildx create --driver docker-container --name "$builder"
    builder_created=true
    if (( $# == 0 )); then
        docker buildx build --builder "$builder" --platform linux/amd64 --output type=cacheonly .
    else
        docker buildx build --builder "$builder" --platform linux/amd64 --load --tag "$tag" .
        {{ invoke }} --set image "$tag" "$@"
    fi

_verify: (_run "lint") _test-rego

[positional-arguments]
_run +COMMAND:
    docker run --rm --platform linux/amd64 {{ docker_args }} {{ config_mounts }} "{{ image }}" "$@"

_catalog:
    docker run --rm --platform linux/amd64 {{ docker_args }} "{{ image }}" catalog

_test-rego:
    docker run --rm --entrypoint conftest -v "$PWD/policies:/policies" {{ image }} verify -p /policies/repo-standards/
    docker run --rm --entrypoint conftest -v "$PWD/policies:/policies" {{ image }} verify -p /policies/compose/

[doc('Validate semgrep rules')]
[group('check')]
test-semgrep:
    uvx semgrep scan --config semgrep-rules/ --validate

[doc('Change impact analysis (blast radius, coupling, criticality)')]
[group('check')]
measure *ARGS:
    uv run --with networkx python3 scripts/blast_radius.py {{ ARGS }}
