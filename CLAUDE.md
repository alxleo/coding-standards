# coding-standards

A Docker image that acts as a seed — drop it into any repo's CI and it tells you what to set up, catches bugs, enforces security, and improves over time as new checks are added.

Built on MegaLinter. Runs identically on Gitea Actions and GitHub Actions.

## Architecture: Three Layers

### 1. Enforcement (linters + security)

43 linters catch code problems. Two tiers:

- **Error tier** (24): blocks build — security, type checking, correctness
- **Warn tier** (19): reports only — formatting, style, schemas

See `docs/catalog.md` for the full generated inventory.

### 2. Structural validation (conftest/Rego policies)

Conftest policies validate structured config files:

- `policies/compose/` — Docker Compose: healthchecks, resource limits, image pinning
- Consumers activate by adding `conftest.toml` in their repo root

### 3. Repo standards (conftest + manifest)

Checks whether a repo is **set up** to benefit from the other layers. A manifest generator scans the repo, conftest evaluates Rego policies against it.

```
scripts/generate-repo-manifest.py  →  repo-manifest.json  →  conftest  →  policies/repo-standards/*.rego
       (gather facts)                  (structured data)      (evaluate)     (declarative policies)
```

33 checks across 6 policy files: Python readiness, security, CI, infrastructure, JS/TS, quality. All `warn` by default. Error messages include remediation steps — executable documentation.

Consumer repos silence warnings with reasons via `.repo-standards.yml`:
```yaml
acknowledged:
  commitlint_config: "uses baked commitlint from image"
```

### Custom semgrep rules

20 rules beyond what MegaLinter's `auto + p/trailofbits` provides:

- **test-quality**: over-mocking, mock call counts, hardcoded dict assertions
- **sql-safety**: string interpolation in SQL (Python + JS)
- **silent-fallbacks**: empty catches, bare except, fallbacks without comments
- **python-typing**: bare `dict` params/returns (sync + async)
- **shell-complexity**: jq-in-shell nudges toward Python
- **shell-hygiene, compose-security, justfile-safety, yaml-env-vars**

## Key Concepts

**Consumer repos** inherit the baseline via EXTENDS URL in `.mega-linter.yml`. They override with `_CONFIG_FILE` (one line, MegaLinter auto-passes it as CLI flag). Never use `_ARGUMENTS` for config paths — it blocks consumer overrides.

**EXTENDS merges arrays** — consumers must not override array-valued keys containing absolute image paths. Either omit (inherit) or stop using EXTENDS.

**The catalog** (`docs/catalog.md`) is auto-generated from config files by `scripts/generate-catalog.py`. It IS the source of truth — not a doc to maintain.

## Quick start for consumers

```yaml
# .github/workflows/lint.yml
steps:
  - uses: actions/checkout@v4
    with:
      fetch-depth: 0
  - uses: alxleo/coding-standards/docker-action@v1
```

```yaml
# .mega-linter.yml
EXTENDS:
  - https://raw.githubusercontent.com/alxleo/coding-standards/main/.mega-linter-default.yml
```

Local commands (no setup — the image is the CLI):

```bash
docker run --rm -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards:latest lint ruff
docker run --rm -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards:latest fix
docker run --rm -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards:latest standards
docker run --rm -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards:latest help
```

Full consumer guide: [docs/consumer-guide.md](https://github.com/alxleo/coding-standards/blob/main/docs/consumer-guide.md)
Decision rationale: [docs/config-decisions.md](https://github.com/alxleo/coding-standards/blob/main/docs/config-decisions.md)

## Repository layout

```
Dockerfile                          # MegaLinter cupcake + 13 custom tools
.mega-linter-default.yml            # Baseline config (inherited via EXTENDS)
docker-action/action.yml            # Composite action for CI

plugins/                            # 14 MegaLinter plugin descriptors
  repo-standards.megalinter-descriptor.yml  # Repo standards plugin
  conftest.megalinter-descriptor.yml        # Compose validation plugin
  [12 more tool plugins]

policies/
  compose/                          # Compose file validation (healthchecks, resources, images)
  repo-standards/                   # Repo setup validation (33 checks, 6 categories)
    python.rego, security.rego, ci.rego, infrastructure.rego, javascript.rego, quality.rego
    *_test.rego                     # Rego unit tests (conftest verify)
    helpers.rego                    # Shared: acknowledged() helper

semgrep-rules/                      # 18 custom rules (6 files)
lint-configs-626465/                # Baked linter configs (ruff, shellcheck, yamllint, etc.)
scripts/
  generate-repo-manifest.py         # Manifest generator for repo standards
  generate-catalog.py               # Auto-generates docs/catalog.md
  report-statuses.py                # Posts per-linter commit statuses (Gitea + GitHub)
  ci/check-drift.sh                 # Generic generated-file drift checker
  ci/check-expiry.py                # Expiry/TTL enforcement for date markers

docs/
  catalog.md                        # GENERATED — full inventory of all checks
  consumer-guide.md                 # Getting started + customization + contributing
  config-decisions.md               # Every decision with rationale
  archive/                          # Historical: migration plan, old architecture decisions

.ci.json                            # Data-driven smoke tests (tool --version + policy tests)
.github/workflows/
  docker-build.yml                  # Build + push image to GHCR (weekly trivy scan)
  ci.yml                            # Self-test via legacy lint workflow
  lint.yml                          # Legacy reusable workflow (being replaced by Docker image)
```

## Contributing new checks

1. **Where does it live?**
   - File/config presence → `policies/repo-standards/` + manifest field
   - Code pattern → `semgrep-rules/`
   - Config content validation → `policies/compose/`
   - Code quality rule → `lint-configs-626465/ruff.toml`

2. **Add the check** (Rego policy, semgrep rule, or ruff category)
3. **Add tests** (`conftest verify`, `semgrep --validate`)
4. **Regenerate catalog**: `python3 scripts/generate-catalog.py`
5. **Test against a real repo**: `python3 scripts/generate-repo-manifest.py ~/path/to/repo`

## Developing the image

```bash
docker build --platform linux/amd64 -t coding-standards:test .
uvx ruff check --config lint-configs-626465/ruff.toml .
uvx semgrep scan --config semgrep-rules/ .
just docker-lint              # full suite
just docker-lint-only PYTHON_RUFF  # single linter
```

## Running tests

```bash
just test                     # pytest + bats
conftest verify -p policies/repo-standards/   # Rego unit tests (needs conftest or Docker)
python3 scripts/generate-catalog.py --check   # catalog drift
```
