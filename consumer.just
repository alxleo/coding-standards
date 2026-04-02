# coding-standards consumer recipes — import into your justfile:
#   import? "/path/to/consumer.just"
# Or extract from the image:
#   docker run --rm ghcr.io/alxleo/coding-standards:latest cat /opt/coding-standards/consumer.just > consumer.just

# Default image — consumers can override: just --set cs-image ghcr.io/alxleo/coding-standards:v1.8
cs-image := "ghcr.io/alxleo/coding-standards:latest"
cs-workspace := justfile_directory()

# ── Core commands ────────────────────────────────────────────

# Run full lint suite
cs-lint *ARGS:
    docker run --rm -v "{{ cs-workspace }}:/tmp/lint" -e DEFAULT_WORKSPACE=/tmp/lint {{ cs-image }} {{ ARGS }}

# Run a single linter (e.g. cs-lint-one ruff, cs-lint-one shellcheck)
cs-lint-one LINTER:
    docker run --rm -v "{{ cs-workspace }}:/tmp/lint" -e DEFAULT_WORKSPACE=/tmp/lint {{ cs-image }} lint {{ LINTER }}

# Auto-fix all fixable issues
cs-fix:
    docker run --rm -v "{{ cs-workspace }}:/tmp/lint" -e DEFAULT_WORKSPACE=/tmp/lint {{ cs-image }} fix

# Run repo-standards checks only
cs-standards:
    docker run --rm -v "{{ cs-workspace }}:/tmp/lint" -e DEFAULT_WORKSPACE=/tmp/lint {{ cs-image }} standards

# Show which config each linter uses
cs-show-config:
    docker run --rm -v "{{ cs-workspace }}:/tmp/lint" -e DEFAULT_WORKSPACE=/tmp/lint {{ cs-image }} show-config

# Show full catalog of checks
cs-catalog:
    docker run --rm {{ cs-image }} catalog

# ── Setup guides (progressive disclosure) ────────────────────

# Show help for a topic: cs-help, cs-help semgrep, cs-help conftest, etc.
cs-help TOPIC="overview":
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{ TOPIC }}" in
    overview)
        echo "coding-standards — centralized linting image"
        echo ""
        echo "Commands:"
        echo "  just cs-lint              Full lint suite"
        echo "  just cs-lint-one ruff     Single linter"
        echo "  just cs-fix               Auto-fix all"
        echo "  just cs-standards         Repo setup checks"
        echo "  just cs-show-config       Which config each linter uses"
        echo "  just cs-catalog           Full check inventory"
        echo ""
        echo "Setup guides (just cs-help <topic>):"
        echo "  semgrep     Add custom pattern-matching rules"
        echo "  conftest    Add custom structural validation policies"
        echo "  ruff        Override Python lint rules"
        echo "  eslint      Override JS/TS lint rules"
        echo "  override    Override any linter's config"
        echo "  suppress    Suppress specific findings"
        echo "  gitignore   What to add to .gitignore"
        echo ""
        echo "Docs: https://github.com/alxleo/coding-standards/blob/main/docs/consumer-guide.md"
        ;;
    semgrep)
        echo "=== Adding custom semgrep rules ==="
        echo ""
        echo "Drop a .semgrep/ directory in your repo. Rules are auto-discovered"
        echo "and run alongside the baked rules (security-audit, trailofbits, custom)."
        echo ""
        echo "  mkdir -p .semgrep"
        echo "  cat > .semgrep/my-rules.yml << 'EOF'"
        echo "  rules:"
        echo "    - id: no-hardcoded-api-key"
        echo '      pattern: "api_key = \"...\""'
        echo "      message: Use environment variables for API keys"
        echo "      languages: [python]"
        echo "      severity: ERROR"
        echo "  EOF"
        echo ""
        echo "Suppress a rule inline: # nosemgrep: coding-standards.rule-name"
        echo "Suppress via config:    REPOSITORY_SEMGREP_ARGUMENTS: [--exclude-rule=rules.custom.coding-standards.rule-name]"
        ;;
    conftest)
        echo "=== Adding custom conftest/Rego policies ==="
        echo ""
        echo "Add policy/ + conftest.toml in your repo. Policies run alongside"
        echo "the baked repo-standards and compose policies automatically."
        echo ""
        echo "  mkdir -p policy/compose"
        echo '  echo "parser = \"yaml\"" > conftest.toml'
        echo "  cat > policy/compose/resources.rego << 'EOF'"
        echo "  package compose.resources"
        echo "  import rego.v1"
        echo '  deny contains msg if {'
        echo '      some name, svc in input.services'
        echo '      not svc.deploy.resources.limits.memory'
        echo '      msg := sprintf("service %q missing memory limit", [name])'
        echo '  }'
        echo "  EOF"
        echo ""
        echo "To extend baked repo-standards (promote warnings to errors):"
        echo "  policy/repo-standards/local.rego:"
        echo "    package repo_standards.local"
        echo "    import data.repo_standards.python"
        echo "    deny := python.warn"
        ;;
    ruff)
        echo "=== Overriding Python (ruff) config ==="
        echo ""
        echo "Add ruff.toml to your repo root. The baked config is used as fallback."
        echo "Use ruff's extend mechanism to build on the baseline:"
        echo ""
        echo "  # ruff.toml"
        echo '  extend = ".mega-linter-config/ruff.toml"  # inherit baseline'
        echo '  [lint]'
        echo '  select = ["ALL"]  # or add specific categories'
        echo ""
        echo "Or set in .mega-linter.yml:"
        echo "  PYTHON_RUFF_CONFIG_FILE: ruff.toml"
        echo ""
        echo "Migration recipe (fix + suppress existing findings):"
        echo "  uvx ruff check --fix . && uvx ruff check --add-noqa ."
        ;;
    eslint)
        echo "=== Overriding JS/TS (ESLint) config ==="
        echo ""
        echo "Add eslint.config.mjs to your repo root."
        echo "Set in .mega-linter.yml:"
        echo "  JAVASCRIPT_ES_CONFIG_FILE: eslint.config.mjs"
        echo "  TYPESCRIPT_ES_CONFIG_FILE: eslint.config.mjs"
        echo ""
        echo "The baked config includes: unicorn, security, sonarjs, i18next plugins."
        echo "Your config fully replaces it — import what you need."
        ;;
    override)
        echo "=== Overriding any linter's config ==="
        echo ""
        echo "Set <LINTER>_CONFIG_FILE in your .mega-linter.yml:"
        echo ""
        echo "  PYTHON_RUFF_CONFIG_FILE: ruff.toml"
        echo "  YAML_YAMLLINT_CONFIG_FILE: .yamllint"
        echo "  REPOSITORY_GITLEAKS_CONFIG_FILE: .gitleaks.toml"
        echo "  ANSIBLE_ANSIBLE_LINT_CONFIG_FILE: .ansible-lint"
        echo ""
        echo "Your file takes precedence over the baked config."
        echo "Run 'just cs-show-config' to see which config each linter uses."
        ;;
    suppress)
        echo "=== Suppressing specific findings ==="
        echo ""
        echo "Semgrep:   # nosemgrep: coding-standards.rule-name"
        echo "Ruff:      # noqa: E501"
        echo "Shellcheck: # shellcheck disable=SC2086"
        echo "Trivy:     Add CVE to .trivyignore"
        echo "Gitleaks:  Add to .gitleaksignore"
        echo ""
        echo "Disable a linter entirely in .mega-linter.yml:"
        echo "  DISABLE_LINTERS:"
        echo "    - TERRAFORM_TFLINT"
        echo ""
        echo "Demote to warning (won't block CI):"
        echo "  DISABLE_ERRORS_LINTERS:"
        echo "    - PYTHON_PYRIGHT"
        ;;
    gitignore)
        echo "=== Recommended .gitignore entries ==="
        echo ""
        echo "# coding-standards lint artifacts"
        echo ".mega-linter-config/    # baked linter configs"
        echo "megalinter-reports/     # lint output"
        echo "repo-manifest.json      # generated for repo-standards"
        echo ".lycheecache            # link checker cache"
        echo ".ruff_cache/            # ruff cache"
        echo ".editorconfig           # only if you don't have your own"
        echo ".v8rrc.yml              # symlink to .mega-linter-config/"
        ;;
    *)
        echo "Unknown topic: {{ TOPIC }}"
        echo "Run 'just cs-help' for available topics."
        exit 1
        ;;
    esac
