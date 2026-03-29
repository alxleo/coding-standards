# coding-standards — dev tasks for this repo only.
# Consumers use the GitHub Action, not this justfile.

set unstable := true

pre-commit-config := "lint-configs-626465/.pre-commit-config.yaml"

# ── Docker lint (MegaLinter) ────────────────────────────────
# Primary lint path — runs the same image as CI

image := "coding-standards:prototype"

[doc('Run full MegaLinter suite via Docker')]
[group('docker-lint')]
docker-lint:
    docker run --rm -v "$PWD:/tmp/lint" {{ image }}

[doc('Run MegaLinter with auto-fix enabled')]
[group('docker-lint')]
docker-lint-fix:
    docker run --rm -v "$PWD:/tmp/lint" -e APPLY_FIXES=all {{ image }}

[doc('Run a single linter (e.g. just docker-lint-only BASH_SHELLCHECK)')]
[group('docker-lint')]
docker-lint-only linter:
    docker run --rm -v "$PWD:/tmp/lint" -e ENABLE_LINTERS={{ linter }} {{ image }}

[doc('Show results from last MegaLinter run (no re-run)')]
[group('docker-lint')]
docker-lint-report:
    @python3 -c "\
    import json, sys; \
    r = json.load(open('megalinter-reports/mega-linter-report.json')); \
    blockers = [l for l in r['linters'] if l['return_code'] != 0]; \
    warns = [l for l in r['linters'] if l['return_code'] == 0 and l.get('total_number_errors', 0) > 0]; \
    passing = [l for l in r['linters'] if l['return_code'] == 0 and l.get('total_number_errors', 0) == 0]; \
    print(f'BLOCKING ({len(blockers)}):'); \
    [print(f'  ❌ {l[\"name\"]:35s} {l.get(\"total_number_errors\",0)} errors') for l in blockers]; \
    print(f'WARNINGS ({len(warns)}):'); \
    [print(f'  ⚠️  {l[\"name\"]:35s} {l.get(\"total_number_errors\",0)} issues') for l in warns]; \
    print(f'PASSING ({len(passing)}):'); \
    [print(f'  ✅ {l[\"name\"]}') for l in passing]; \
    "

[doc('Show detailed errors for a specific linter from last run')]
[group('docker-lint')]
docker-lint-errors linter:
    @python3 -c "\
    import json; \
    r = json.load(open('megalinter-reports/mega-linter-report.json')); \
    matches = [l for l in r['linters'] if '{{ linter }}'.upper() in l['name']]; \
    [print(f'{l[\"name\"]}: {l[\"status\"]} ({l.get(\"total_number_errors\",0)} errors)\n') for l in matches]; \
    " && cat megalinter-reports/linters_logs/*{{ linter }}* 2>/dev/null || echo "No log found for {{ linter }}"

# ── Pre-commit lint (legacy) ───────────────────────────────

[doc('Run the full lint suite locally (mirrors CI)')]
[group('lint')]
lint: _setup-pre-commit
    #!/usr/bin/env bash
    set -uo pipefail
    rc=0

    run_group() {
        local name="$1"; shift
        printf "%-30s" "$name"
        if "$@" > /dev/null 2>&1; then
            echo "pass"
        else
            echo "FAIL"
            rc=1
        fi
    }

    # Pre-commit groups
    run_group "File hygiene" uvx pre-commit run check-yaml --all-files -c {{ pre-commit-config }}
    run_group "YAML (yamllint)" uvx pre-commit run yamllint --all-files -c {{ pre-commit-config }}
    run_group "Secret scanning" uvx pre-commit run gitleaks --all-files -c {{ pre-commit-config }}
    run_group "GitHub Actions" uvx pre-commit run actionlint --all-files -c {{ pre-commit-config }}
    run_group "Zizmor" uvx pre-commit run zizmor --all-files -c {{ pre-commit-config }}
    run_group "Markdown" uvx pre-commit run markdownlint-cli2 --all-files -c {{ pre-commit-config }}
    run_group "Prettier" uvx pre-commit run prettier --all-files -c {{ pre-commit-config }}
    run_group "Shell hygiene" uvx pre-commit run shell-hygiene --all-files -c {{ pre-commit-config }}

    if [ $rc -ne 0 ]; then
        echo ""
        echo "Some checks failed. Run 'just lint-verbose' for details."
        exit 1
    fi
    echo ""
    echo "All checks passed."

[doc('Run the full lint suite with verbose output')]
[group('lint')]
lint-verbose: _setup-pre-commit
    uvx pre-commit run --all-files -c {{ pre-commit-config }}

[doc('Run a single lint group (e.g. just lint-group actionlint)')]
[group('lint')]
lint-group hook: _setup-pre-commit
    uvx pre-commit run {{ hook }} --all-files -c {{ pre-commit-config }}

[doc('Validate all workflow YAML')]
[group('lint')]
lint-yaml:
    uv run --no-project --with pyyaml python3 -c "import yaml, glob; [yaml.safe_load(open(f)) or print(f'  valid: {f}') for f in glob.glob('.github/workflows/*.yml')]"

# ── Tests ─────────────────────────────────────────────────────

[doc('Run all tests (pytest + bats)')]
[group('test')]
test:
    uv run --no-project --with pyyaml pytest test/ -v
    npx bats@1 test/*.bats

# ── Setup ───────────────────────────────────────────────────
# Only configs without --config flag support need copying to root

[private]
_copied-configs := ".shellcheckrc .editorconfig"

[doc('Install pre-commit hooks and apply configs')]
_setup-pre-commit:
    #!/usr/bin/env bash
    set -euo pipefail
    # Create symlink so .coding-standards/ paths in pre-commit args resolve
    if [ ! -e .coding-standards ]; then
        ln -s . .coding-standards
    fi
    uvx pre-commit install-hooks -c {{ pre-commit-config }} > /dev/null 2>&1
    # Copy configs that don't support --config (shellcheckrc, editorconfig)
    cs="lint-configs-626465"
    for cfg in {{ _copied-configs }}; do
        if [ ! -f "$cfg" ] && [ -f "$cs/$cfg" ]; then
            cp "$cs/$cfg" "$cfg"
        fi
    done

[doc('Remove temporarily copied lint configs and symlink')]
[group('lint')]
clean:
    #!/usr/bin/env bash
    for cfg in {{ _copied-configs }}; do
        if [ -f "$cfg" ]; then rm "$cfg"; echo "  removed $cfg"; fi
    done
    if [ -L .coding-standards ]; then rm .coding-standards; echo "  removed .coding-standards symlink"; fi
