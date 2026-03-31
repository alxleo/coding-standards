<!-- GENERATED — do not edit. Run: python3 scripts/generate-catalog.py -->
# Coding Standards Catalog

Complete inventory of what the coding-standards image checks.
Generated from config files — this IS the source of truth.

## Linters (54 total)

### Error tier (24 — blocks build)

- BASH_SHELLCHECK
- PYTHON_RUFF
- PYTHON_PYRIGHT
- DOCKERFILE_HADOLINT
- ACTION_ACTIONLINT
- TERRAFORM_TFLINT
- REPOSITORY_GITLEAKS
- REPOSITORY_SEMGREP
- REPOSITORY_TRIVY_CUSTOM
- REPOSITORY_CONFTEST
- REPOSITORY_ZIZMOR
- REPOSITORY_COMMITLINT
- JAVASCRIPT_ES
- TYPESCRIPT_ES
- JSX_ESLINT
- TSX_ESLINT
- TYPESCRIPT_TSC
- REPOSITORY_KNIP
- REPOSITORY_DEPENDENCY_CRUISER
- REPOSITORY_NPM_AUDIT
- REPOSITORY_LICENSE_CHECKER
- REPOSITORY_CADDY_FMT
- REPOSITORY_JUST_FMT
- REPOSITORY_GIT_DIFF

### Warn tier (30 — reports only)

- BASH_SHFMT
- PYTHON_VULTURE
- YAML_YAMLLINT
- YAML_PRETTIER
- YAML_V8R
- JSON_PRETTIER
- JSON_V8R
- MARKDOWN_MARKDOWNLINT
- DOCKERFILE_DCLINT
- EDITORCONFIG_EDITORCONFIG_CHECKER
- COPYPASTE_PMD_CPD
- SPELL_CODESPELL
- SPELL_LYCHEE
- REPOSITORY_REPO_STANDARDS
- JAVASCRIPT_PRETTIER
- TYPESCRIPT_PRETTIER
- REPOSITORY_TYPE_COVERAGE
- REPOSITORY_OXLINT
- REPOSITORY_PUBLINT
- REPOSITORY_ATTW
- REPOSITORY_DEPTRY
- REPOSITORY_IMPORT_LINTER
- CSS_STYLELINT
- SQL_SQLFLUFF
- API_SPECTRAL
- ANSIBLE_ANSIBLE_LINT
- KUBERNETES_KUBECONFORM
- REPOSITORY_LS_LINT
- ENV_DOTENV_LINTER
- MAKEFILE_CHECKMAKE

## Ruff rule categories (29)

- E — pycodestyle errors
- W — pycodestyle warnings
- F — pyflakes
- I — isort
- B — flake8-bugbear
- S — flake8-bandit (security)
- UP — pyupgrade
- SIM — flake8-simplify
- C4 — flake8-comprehensions
- RUF — ruff-specific rules
- BLE — blind exceptions (except Exception swallowing errors)
- DTZ — naive datetimes (datetime.now() without timezone)
- PERF — performance anti-patterns (loop-append vs comprehension)
- FURB — modernization (patterns Python 3.11+ handles natively)
- RET — return style (unnecessary elif after return)
- PLW1510 — subprocess.run without check= (unchecked exit codes)
- PLW2901 — loop variable overwritten inside loop body
- T20 — print statements (use logging in application code)
- PLR2004 — magic values (use named constants)
- PLC0415 — imports not at top of file
- ARG — unused function arguments
- FBT — boolean positional args (use keyword-only)
- PIE — flake8-pie (unnecessary spread, reimported names, no-op pass)
- ISC — implicit string concatenation (catches accidental tuple-in-list)
- A — flake8-builtins (shadowing list, dict, type, id — LLMs do this constantly)
- PGH — pygrep-hooks (blanket type-ignore / noqa without codes)
- RSE — flake8-raise (unnecessary parens in raise)
- PT011 — pytest.raises() without match= (overly broad exception catch in tests)
- N — pep8-naming (N999 catches hyphenated/non-importable module filenames)

## Semgrep rules (22)

| Rule | Severity | Source | Description |
|------|----------|--------|-------------|
| python-deep-nesting | WARNING | complexity.yml | Function $FUNC has 4+ levels of nesting. Extract inner logic into helper functions or use early returns to flatten the structure. |
| no-privileged-containers | ERROR | compose-security.yml | Do not use privileged: true. Use specific capabilities (cap_add) or security_opt instead. |
| no-env-file-secrets | WARNING | compose-security.yml | Do not use env_file to inject secrets. Use Docker secrets or SOPS-encrypted environment variables instead. |
| justfile-eval-usage | WARNING | justfile-safety.yml | Avoid eval in justfile recipes. Use direct command invocation or just's built-in variable interpolation. |
| justfile-curl-pipe-sh | ERROR | justfile-safety.yml | Piping curl output to sh/bash is a security risk. Download to a file, verify checksum, then execute. |
| python-no-bare-print | WARNING | observability.yml | Bare print() in application code. Use structured logging (structlog or logging with JSON formatter) for production code. Print statements are invisible to log aggregators. |
| javascript-no-console-log | WARNING | observability.yml | console.log() in application code. Use a structured logger (pino, winston) for production code. Console output is unstructured and invisible to log aggregators. |
| no-bare-dict-params | WARNING | python-typing.yml | Use a TypedDict or specific dict[K, V] instead of bare `dict`. Bare dict parameters lose all type information — callers can pass anything, and the function body has no contract to enforce. |
| no-bare-dict-return | WARNING | python-typing.yml | Use a TypedDict or specific dict[K, V] instead of bare `dict` return. Callers get no type information about the returned structure. |
| shell-json-parsing | INFO | shell-complexity.yml | JSON parsing in shell with jq pipeline. Consider Python instead — shell + jq is brittle, hard to test, and lacks error handling. Python's json module does the same with types and try/except. |
| no-bare-python | WARNING | shell-hygiene.yml | Use 'uv run python3' instead of bare 'python3' to ensure consistent virtual environment and dependency management. |
| pin-npm-versions | WARNING | shell-hygiene.yml | npx invocations must pin a version (e.g., npx jscpd@4.0.8). Unpinned npx pulls latest, which breaks reproducibility. |
| python-silent-fallback-or | INFO | silent-fallbacks.yml | Silent fallback: `or $DEFAULT` may hide a bug. If the empty/falsy case is expected, add `# nosemgrep: python-silent-fallback-or` to acknowledge the intent. |
| python-bare-except-pass | WARNING | silent-fallbacks.yml | Bare except with pass swallows all errors including KeyboardInterrupt. Catch a specific exception, or at minimum log the error. |
| javascript-silent-catch | WARNING | silent-fallbacks.yml | Empty catch block silently swallows errors. Either handle the error, re-throw, or add a comment explaining why it's safe to ignore. |
| python-sql-string-interpolation | ERROR | sql-safety.yml | SQL query uses string interpolation — use parameterized queries instead. String interpolation in SQL enables injection attacks, even for "trusted" internal data. Use ? placeholders or a query builder. |
| javascript-sql-string-interpolation | ERROR | sql-safety.yml | SQL query uses template literal interpolation — use parameterized queries instead. Use ? placeholders or a query builder. |
| test-over-mocking | WARNING | test-quality.yml | Test $FUNC uses 4+ @patch decorators. Tests that mock everything verify mocks, not code. Consider testing with fewer mocks or using integration tests. |
| test-mock-call-count | WARNING | test-quality.yml | Asserting exact call count is brittle — breaks on any refactor. Test the behavior (output, side effects) instead of how many times something was called. |
| test-mock-assert-called-with-literals | INFO | test-quality.yml | assert_called_with verifies implementation details (exact args). Prefer testing the observable outcome instead of how the code internally calls its dependencies. |
| test-hardcoded-dict-assertion | WARNING | test-quality.yml | Large hardcoded dict assertion is likely tautological — copied from a single run. Test specific properties or use snapshot testing. |
| unexpanded-env-var-in-yaml | WARNING | yaml-env-vars.yml | YAML value contains ${VAR} that won't be expanded by most YAML-consuming tools. Use envsubst, the tool's native env mechanism, or inject the value at runtime. |

## Compose policies (16)

- **warn**: service '%s' depends_on '%s' with condition: service_started — use service_healthy to wait for readiness (depends.rego)
- **warn**: service '%s' depends_on '%s' without condition — defaults to service_started (race condition). Use condition: service_healthy (depends.rego)
- **deny**: service '%s' missing healthcheck (healthcheck.rego)
- **warn**: service '%s' has healthcheck explicitly disabled (healthcheck.rego)
- **deny**: service '%s' uses own image '%s' without :latest tag (images.rego)
- **deny**: service '%s' missing container_name (resources.rego)
- **deny**: service '%s' missing memory limit (deploy.resources.limits.memory or mem_limit) (resources.rego)
- **warn**: service '%s' has unnamed volume '%s' — use named volumes for persistence (runtime.rego)
- **warn**: service '%s' uses host networking — loses container isolation (runtime.rego)
- **warn**: service '%s' has no restart policy — won't recover from crashes (runtime.rego)
- **deny**: service '%s' is privileged — use specific cap_add instead (runtime.rego)
- **warn**: service '%s' uses host bind mount '%s' — consider named volumes for portability (runtime.rego)
- **deny**: service '%s' mounts Docker socket — gives full host control. Use read-only (:ro) at minimum (security.rego)
- **warn**: service '%s' missing security_opt: no-new-privileges:true (security.rego)
- **warn**: service '%s' exposes port %s to all interfaces — bind to 127.0.0.1 unless intentionally public (security.rego)
- **deny**: service '%s' mounts sensitive host path '%s' (security.rego)

## Repo standards (45)

- **warn**: .mega-linter.yml not found (ci.rego)
- **warn**: .mega-linter.yml exists but has no EXTENDS URL (ci.rego)
- **warn**: No workflow references coding-standards/docker-action (ci.rego)
- **warn**: No workflow uses fetch-depth: 0 (ci.rego)
- **warn**: persist-credentials: false not set in checkout — security best practice (ci.rego)
- **warn**: Not all GitHub Actions are SHA-pinned (ci.rego)
- **warn**: coding-standards repo-standards checks active (guide.rego)
- **warn**: conftest.toml not found (infrastructure.rego)
- **warn**: .editorconfig not found — ensures consistent formatting across editors (infrastructure.rego)
- **warn**: .ci.json not found (infrastructure.rego)
- **warn**: renovate.json not found (infrastructure.rego)
- **warn**: tsconfig.json not found — TypeScript needs config for type checking (javascript.rego)
- **warn**: No ESLint config found — linting config needed for JS/TS code (javascript.rego)
- **warn**: eslint-plugin-jest not in dependencies (javascript.rego)
- **warn**: .nvmrc not found — pin Node version for consistent builds across machines (javascript.rego)
- **warn**: No i18n framework detected (i18next, react-intl, next-intl) (javascript.rego)
- **warn**: No structured logging library (pino, winston, bunyan) (javascript.rego)
- **warn**: zod not in dependencies (javascript.rego)
- **warn**: @stryker-mutator/core not in dependencies (javascript.rego)
- **warn**: No health endpoint found (/health, /healthz, /ready) (observability.rego)
- **warn**: No Prometheus client found — /metrics endpoint enables monitoring dashboards (observability.rego)
- **warn**: No error tracking SDK found (Sentry, Datadog) — errors in production need alerting (observability.rego)
- **warn**: No tracing/OpenTelemetry SDK found (observability.rego)
- **warn**: pyrightconfig.json not found (python.rego)
- **warn**: ruff.toml not found (python.rego)
- **warn**: pytest-randomly not in dependencies (python.rego)
- **warn**: tests/ directory exists but no test framework in pyproject.toml (python.rego)
- **warn**: %d Python file(s) have hyphens in their names (python.rego)
- **warn**: No structured logging library (structlog, python-json-logger) (python.rego)
- **warn**: pydantic not in dependencies (python.rego)
- **warn**: import-linter not in dependencies (python.rego)
- **warn**: import-linter installed but no contracts defined (python.rego)
- **warn**: hypothesis not in dependencies (python.rego)
- **warn**: No CI workflow directory found (.github/workflows/ or .gitea/workflows/) (quality.rego)
- **warn**: .pre-commit-config.yaml not found (quality.rego)
- **warn**: No commitlint config found — conventional commits make history readable (quality.rego)
- **warn**: .envrc not found (quality.rego)
- **warn**: %d suppression comments found across codebase (quality.rego)
- **warn**: No Makefile or justfile found (quality.rego)
- **warn**: No tests/ directory but Python scripts present (quality.rego)
- **warn**: %d shell script(s) exceed 50 lines (quality.rego)
- **warn**: .gitleaks.toml not found (security.rego)
- **warn**: trivy.yaml not found (security.rego)
- **warn**: .sops.yaml not found (security.rego)
- **warn**: .gitignore does not cover .decrypted/ (security.rego)
