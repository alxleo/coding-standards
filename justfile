# coding-standards — dev tasks for this repo only.
# Consumers use the GitHub Action, not this justfile.

set unstable := true

pre-commit-config := "lint-configs-626465/.pre-commit-config.yaml"

# ── Lint ────────────────────────────────────────────────────

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
    run_group "File hygiene" uvx pre-commit run check-yaml --all-files -c {{pre-commit-config}}
    run_group "YAML (yamllint)" uvx pre-commit run yamllint --all-files -c {{pre-commit-config}}
    run_group "Secret scanning" uvx pre-commit run gitleaks --all-files -c {{pre-commit-config}}
    run_group "Typo detection" uvx pre-commit run typos --all-files -c {{pre-commit-config}}
    run_group "GitHub Actions" uvx pre-commit run actionlint --all-files -c {{pre-commit-config}}
    run_group "Zizmor" uvx pre-commit run zizmor --all-files -c {{pre-commit-config}}
    run_group "Markdown" uvx pre-commit run markdownlint-cli2 --all-files -c {{pre-commit-config}}
    run_group "Shell hygiene" uvx pre-commit run pin-npm-versions --all-files -c {{pre-commit-config}}

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
    uvx pre-commit run --all-files -c {{pre-commit-config}}

[doc('Run a single lint group (e.g. just lint-group actionlint)')]
[group('lint')]
lint-group hook: _setup-pre-commit
    uvx pre-commit run {{hook}} --all-files -c {{pre-commit-config}}

[doc('Validate all workflow YAML')]
[group('lint')]
lint-yaml:
    python3 -c "import yaml, glob; [yaml.safe_load(open(f)) or print(f'  valid: {f}') for f in glob.glob('.github/workflows/*.yml')]"

# ── E2E ──────────────────────────────────────────────────────

[doc('Run the full CI workflow locally via act (requires Docker)')]
[group('test')]
lint-e2e:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! command -v act &>/dev/null; then
        echo "act is not installed. Install from https://github.com/nektos/act"
        exit 1
    fi
    echo "Running CI workflow locally via act..."
    act push -W .github/workflows/ci.yml --container-architecture linux/amd64

# ── CI script tests ──────────────────────────────────────────

[doc('Test extracted CI scripts (lint-run, summary)')]
[group('test')]
test-ci-scripts:
    #!/usr/bin/env bash
    set -euo pipefail
    rc=0

    printf "%-30s" "lint-run.sh (pass case)"
    if scripts/ci/lint-run.sh test-pass true > /dev/null 2>&1; then
        echo "pass"
    else
        echo "FAIL"; rc=1
    fi

    printf "%-30s" "lint-run.sh (fail case)"
    if ! scripts/ci/lint-run.sh test-fail false > /dev/null 2>&1; then
        echo "pass"
    else
        echo "FAIL (should have failed)"; rc=1
    fi

    printf "%-30s" "summary.sh (all pass)"
    if HYGIENE=success CRUFT=success GITLEAKS=success TYPOS=success \
       YAML=success ACTIONS=success MARKDOWN=success COMMITLINT=success \
       PYTHON=success SHELL=success JUSTFILE=success JSCPD=success \
       TRIVY=success SEMGREP=success EXTRA=skipped \
       scripts/ci/summary.sh > /dev/null 2>&1; then
        echo "pass"
    else
        echo "FAIL"; rc=1
    fi

    printf "%-30s" "summary.sh (with failure)"
    if ! HYGIENE=failure CRUFT=success GITLEAKS=success TYPOS=success \
         YAML=success ACTIONS=success MARKDOWN=success COMMITLINT=success \
         PYTHON=success SHELL=success JUSTFILE=success JSCPD=success \
         TRIVY=success SEMGREP=success EXTRA=skipped \
         scripts/ci/summary.sh > /dev/null 2>&1; then
        echo "pass"
    else
        echo "FAIL (should have failed)"; rc=1
    fi

    if [ $rc -ne 0 ]; then exit 1; fi
    echo ""
    echo "All CI script tests passed."

# ── Setup ───────────────────────────────────────────────────

# Configs that get temporarily copied to root for local linting
_copied-configs := ".gitleaks.toml .markdownlint-cli2.yaml .shellcheckrc .yamllint .hadolint.yaml .jscpd.json .prettierrc .editorconfig commitlint.config.mjs"

[doc('Install pre-commit hooks and apply configs')]
_setup-pre-commit:
    #!/usr/bin/env bash
    set -euo pipefail
    uvx pre-commit install-hooks -c {{pre-commit-config}} > /dev/null 2>&1
    # Apply lint configs that don't already exist (mirrors CI behavior)
    cs="lint-configs-626465"
    for cfg in {{_copied-configs}}; do
        if [ ! -f "$cfg" ] && [ -f "$cs/$cfg" ]; then
            cp "$cs/$cfg" "$cfg"
        fi
    done

[doc('Remove temporarily copied lint configs')]
[group('lint')]
clean:
    #!/usr/bin/env bash
    for cfg in {{_copied-configs}}; do
        if [ -f "$cfg" ]; then rm "$cfg"; echo "  removed $cfg"; fi
    done
