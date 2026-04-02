# coding-standards consumer recipes — import into your justfile:
#   import? "consumer.just"
# Or extract from the image:
#   docker run --rm ghcr.io/alxleo/coding-standards:latest cat /opt/coding-standards/consumer.just > consumer.just

# Default image — consumers can override: just --set cs-image ghcr.io/alxleo/coding-standards:v1.8
cs-image := "ghcr.io/alxleo/coding-standards:latest"
cs-workspace := justfile_directory()
cs-docker := "docker run --rm -v " + cs-workspace + ":/tmp/lint -e DEFAULT_WORKSPACE=/tmp/lint"

# ── Core commands ────────────────────────────────────────────

# Run full lint suite
cs-lint *ARGS:
    {{ cs-docker }} {{ cs-image }} {{ ARGS }}

# Run a single linter (e.g. cs-lint-one ruff, cs-lint-one shellcheck)
cs-lint-one LINTER:
    {{ cs-docker }} {{ cs-image }} lint {{ LINTER }}

# Auto-fix all fixable issues
cs-fix:
    {{ cs-docker }} {{ cs-image }} fix

# Run repo-standards checks only
cs-standards:
    {{ cs-docker }} {{ cs-image }} standards

# Show which config each linter uses + detect overrides
cs-show-config:
    {{ cs-docker }} {{ cs-image }} show-config

# Show full catalog of checks
cs-catalog:
    @docker run --rm {{ cs-image }} catalog

# Show last run's warnings (grouped by linter)
cs-warnings:
    {{ cs-docker }} {{ cs-image }} warnings

# Change impact analysis
cs-blast-radius *ARGS:
    {{ cs-docker }} {{ cs-image }} blast-radius {{ ARGS }}

# Pull latest image
cs-update:
    docker pull {{ cs-image }}
    @echo "Updated. Run 'just cs-lint' to use the new image."
    @echo "To update this justfile: docker run --rm {{ cs-image }} cat /opt/coding-standards/consumer.just > consumer.just"

# ── Setup ─────────────────────────────────────────────────────

# One-command setup: creates CI workflow + .gitignore entries
cs-init:
    #!/usr/bin/env bash
    set -euo pipefail

    # Detect CI platform
    if [ -d .gitea ] || [ -d .gitea/workflows ]; then
        CI_DIR=".gitea/workflows"
        PLATFORM="Gitea"
    else
        CI_DIR=".github/workflows"
        PLATFORM="GitHub"
    fi

    # Create workflow if it doesn't exist
    WORKFLOW="$CI_DIR/lint.yml"
    if [ -f "$WORKFLOW" ]; then
        echo "⏭  $WORKFLOW already exists — skipping"
    else
        mkdir -p "$CI_DIR"
        cat > "$WORKFLOW" << 'WORKFLOW_EOF'
    name: Lint
    on:
      push:
        branches: [main]
      pull_request:
    jobs:
      lint:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
            with:
              fetch-depth: 0
          - uses: alxleo/coding-standards/docker-action@v1
    WORKFLOW_EOF
        echo "✅ Created $WORKFLOW ($PLATFORM)"
    fi

    # Add .gitignore entries
    ENTRIES=(".mega-linter-config/" "megalinter-reports/" "repo-manifest.json" ".lycheecache" ".ruff_cache/" ".v8rrc.yml")
    ADDED=0
    for entry in "${ENTRIES[@]}"; do
        if ! grep -qF "$entry" .gitignore 2>/dev/null; then
            echo "$entry" >> .gitignore
            ADDED=$((ADDED + 1))
        fi
    done
    if [ "$ADDED" -gt 0 ]; then
        echo "✅ Added $ADDED entries to .gitignore"
    else
        echo "⏭  .gitignore already has all entries"
    fi

    echo ""
    echo "Done. Next steps:"
    echo "  just cs-lint          Run locally to see findings"
    echo "  just cs-help migrate  Get to green CI fast"

# ── Help (progressive disclosure) ────────────────────────────

# Show help: cs-help, cs-help setup, cs-help semgrep, etc.
cs-help TOPIC="overview":
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{ TOPIC }}" in
    overview)
        cat <<'HELP'
    coding-standards — centralized linting image

    Getting started:
      just cs-help setup        First-time CI + local setup
      just cs-help migrate      Get from 200 errors to green CI

    Commands:
      just cs-lint              Full lint suite
      just cs-lint-one ruff     Single linter
      just cs-fix               Auto-fix all fixable issues
      just cs-standards         Repo setup checks
      just cs-show-config       Which config each linter uses
      just cs-warnings          Warnings from last run
      just cs-catalog           Full check inventory
      just cs-blast-radius      Change impact analysis
      just cs-update            Pull latest image

    Customize (just cs-help <topic>):
      setup       First-time setup (CI + local)
      migrate     Get to green CI fast
      disable     Turn off linters that don't apply
      semgrep     Add custom pattern-matching rules
      conftest    Add custom structural validation policies
      ruff        Override Python lint rules
      eslint      Override JS/TS lint rules
      override    Override any linter's config
      suppress    Suppress specific findings
      debug       Troubleshoot a failing linter
      gitignore   What to add to .gitignore
      local       Running on Mac (native arm64)
    HELP
        ;;
    setup)
        cat <<'HELP'
    === First-time setup ===

    1. Add CI workflow:

      # .github/workflows/lint.yml (or .gitea/workflows/)
      name: Lint
      on: [push, pull_request]
      jobs:
        lint:
          runs-on: ubuntu-latest
          steps:
            - uses: actions/checkout@v4
            - uses: alxleo/coding-standards/docker-action@v1

    2. Add MegaLinter config:

      # .mega-linter.yml
      EXTENDS:
        - https://raw.githubusercontent.com/alxleo/coding-standards/main/.mega-linter-default.yml

      # Disable linters you don't need:
      DISABLE_LINTERS:
        - TERRAFORM_TFLINT      # no terraform
        - ANSIBLE_ANSIBLE_LINT   # no ansible

    3. Add .gitignore entries (run: just cs-help gitignore)

    4. Run locally: just cs-lint

    5. Expect many findings on first run — see: just cs-help migrate
    HELP
        ;;
    migrate)
        cat <<'HELP'
    === Getting to green CI ===

    First run will find many issues. Strategy: fix what's fixable
    automatically, suppress the rest, clean up over time.

    Step 1 — Auto-fix:
      just cs-fix

    Step 2 — Python (ruff): fix + suppress remaining:
      uvx ruff check --fix .
      uvx ruff check --add-noqa .

    Step 3 — Shell (shellcheck): manual fixes or suppress:
      # No auto-fix. Replace [ ] with [[ ]], quote variables, etc.
      # Add # shellcheck disable=SC2086 for specific lines

    Step 4 — Review what's left:
      just cs-lint 2>&1 | grep "❌"

    Each # noqa / # shellcheck disable is a visible TODO.
    Clean them up over time — the count is a health metric.
    HELP
        ;;
    disable)
        cat <<'HELP'
    === Disabling linters that don't apply ===

    In your .mega-linter.yml:

      DISABLE_LINTERS:
        - TERRAFORM_TFLINT       # no terraform files
        - ANSIBLE_ANSIBLE_LINT   # no ansible playbooks
        - KUBERNETES_KUBECONFORM # no k8s manifests
        - REPOSITORY_KNIP       # no JS/TS project
        - TYPESCRIPT_TSC        # no TypeScript
        - SQL_SQLFLUFF          # no SQL files

    Linters auto-activate on file detection, so most inactive
    linters won't run even without disabling. Explicit disable
    is for: faster runs and cleaner output.

    Demote to warning (still runs, won't block CI):
      DISABLE_ERRORS_LINTERS:
        - PYTHON_PYRIGHT        # type errors are advisory
    HELP
        ;;
    semgrep)
        cat <<'HELP'
    === Adding custom semgrep rules ===

    Drop a .semgrep/ directory in your repo. The entrypoint
    auto-discovers it and runs alongside the baked rules.

      mkdir -p .semgrep
      cat > .semgrep/my-rules.yml << 'EOF'
      rules:
        - id: no-hardcoded-api-key
          pattern: "api_key = \"...\""
          message: Use environment variables for API keys
          languages: [python]
          severity: ERROR
      EOF

    Your rule IDs get a .semgrep. prefix from the directory.
    Suppress inline: # nosemgrep: .semgrep.no-hardcoded-api-key

    Baked rule prefixes:
      rules.security-audit.<id>              (OWASP/security)
      rules.trailofbits.<id>                 (audit)
      rules.custom.coding-standards.<id>     (our custom rules)
    HELP
        ;;
    conftest)
        cat <<'HELP'
    === Adding custom conftest/Rego policies ===

    Add policy/ + conftest.toml. Policies run alongside the baked
    repo-standards and compose policies automatically.

      mkdir -p policy/compose
      echo 'parser = "yaml"' > conftest.toml

      cat > policy/compose/resources.rego << 'EOF'
      package compose.resources
      import rego.v1
      deny contains msg if {
          some name, svc in input.services
          not svc.deploy.resources.limits.memory
          msg := sprintf("service '%s' missing memory limit", [name])
      }
      EOF

    To promote baked warnings to errors in your repo:

      # policy/repo-standards/local.rego
      package repo_standards.local
      import data.repo_standards.python
      deny := python.warn
    HELP
        ;;
    ruff)
        cat <<'HELP'
    === Overriding Python (ruff) config ===

    Option 1 — Extend the baseline:
      # ruff.toml
      extend = ".mega-linter-config/ruff.toml"
      [lint]
      select = ["ALL"]  # add categories on top of baseline

    Option 2 — Full replacement:
      # ruff.toml (your own, no extend)
      # Set in .mega-linter.yml:
      PYTHON_RUFF_CONFIG_FILE: ruff.toml

    Migration recipe:
      uvx ruff check --fix . && uvx ruff check --add-noqa .
    HELP
        ;;
    eslint)
        cat <<'HELP'
    === Overriding JS/TS (ESLint) config ===

    Add eslint.config.mjs to your repo root.
    Set in .mega-linter.yml:
      JAVASCRIPT_ES_CONFIG_FILE: eslint.config.mjs
      TYPESCRIPT_ES_CONFIG_FILE: eslint.config.mjs

    Baked config includes: unicorn, security, sonarjs, i18next.
    Your config fully replaces it — import what you need.
    HELP
        ;;
    override)
        cat <<'HELP'
    === Overriding any linter's config ===

    Set <LINTER>_CONFIG_FILE in your .mega-linter.yml:

      PYTHON_RUFF_CONFIG_FILE: ruff.toml
      YAML_YAMLLINT_CONFIG_FILE: .yamllint
      REPOSITORY_GITLEAKS_CONFIG_FILE: .gitleaks.toml
      ANSIBLE_ANSIBLE_LINT_CONFIG_FILE: .ansible-lint
      PYTHON_PYRIGHT_CONFIG_FILE: pyrightconfig.json

    Your file takes precedence over the baked config.
    Run 'just cs-show-config' to see what each linter uses.
    HELP
        ;;
    suppress)
        cat <<'HELP'
    === Suppressing specific findings ===

    Inline suppression (per-line):
      Python (ruff):     # noqa: E501
      Semgrep:           # nosemgrep: coding-standards.rule-name
      Shellcheck:        # shellcheck disable=SC2086
      Type ignore:       # type: ignore[arg-type]

    File-level suppression:
      Trivy:     .trivyignore          (CVE IDs)
      Gitleaks:  .gitleaksignore       (path patterns)
      Codespell: .codespellrc          (word whitelist)

    Disable a linter entirely (.mega-linter.yml):
      DISABLE_LINTERS:
        - TERRAFORM_TFLINT

    Demote to warning (won't block CI):
      DISABLE_ERRORS_LINTERS:
        - PYTHON_PYRIGHT
    HELP
        ;;
    debug)
        cat <<'HELP'
    === Troubleshooting a failing linter ===

    1. See what config each linter uses:
       just cs-show-config

    2. Run a single linter to isolate:
       just cs-lint-one PYTHON_RUFF

    3. Read the detailed log:
       cat megalinter-reports/linters_logs/PYTHON_RUFF-*.log

    4. Run the tool directly (same version as image):
       docker run --rm -v .:/tmp/lint --entrypoint ruff \
         ghcr.io/alxleo/coding-standards:latest \
         check --config .mega-linter-config/ruff.toml /tmp/lint

    5. Check if your config is overriding the baked one:
       just cs-show-config | grep RUFF

    Common issues:
      "no files to lint"  → linter auto-skipped (no matching files)
      "config not found"  → check _CONFIG_FILE path in .mega-linter.yml
      "command not found"  → tool missing from image (file an issue)
    HELP
        ;;
    local)
        cat <<'HELP'
    === Running locally ===

    The image supports native arm64 — no Rosetta on Apple Silicon:
      just cs-lint

    For faster iteration, run tools directly:
      uvx ruff check .
      uvx semgrep scan --config .semgrep/ .
      shellcheck scripts/*.sh

    Pin to a specific version:
      just --set cs-image ghcr.io/alxleo/coding-standards:v1.8 cs-lint
    HELP
        ;;
    gitignore)
        cat <<'HELP'
    === Recommended .gitignore entries ===

    # coding-standards lint artifacts
    .mega-linter-config/
    megalinter-reports/
    repo-manifest.json
    .lycheecache
    .ruff_cache/
    .editorconfig           # only if you don't have your own
    .v8rrc.yml              # symlink to .mega-linter-config/
    HELP
        ;;
    *)
        echo "Unknown topic: {{ TOPIC }}"
        echo "Run 'just cs-help' for available topics."
        exit 1
        ;;
    esac
