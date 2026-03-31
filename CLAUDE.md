# coding-standards

A Docker image that acts as a seed — drop it into any repo's CI and it tells you what to set up, catches bugs, enforces security, and improves over time as new checks are added.

Built on MegaLinter. Runs identically on Gitea Actions and GitHub Actions.

## Architecture: Three Layers

### 1. Enforcement (linters + security)

Linters catch code problems. Two tiers:

- **Error tier**: blocks build — security, type checking, correctness
- **Warn tier**: reports only — formatting, style, schemas

See `docs/catalog.md` for the full generated inventory (counts, rule IDs, descriptions).

### 2. Structural validation (conftest/Rego policies)

Conftest policies validate structured config files:

- `policies/compose/` — Docker Compose: healthchecks, resource limits, image pinning
- Consumers activate by adding `conftest.toml` in their repo root

### 3. Repo standards (conftest + manifest)

Checks whether a repo is **set up** to benefit from the other layers. A manifest generator scans the repo, conftest evaluates Rego policies against it.

```
scripts/generate_repo_manifest.py  →  repo-manifest.json  →  conftest  →  policies/repo-standards/*.rego
       (gather facts)                  (structured data)      (evaluate)     (declarative policies)
```

Checks across 6 policy files: Python readiness, security, CI, infrastructure, JS/TS, quality. All `warn` by default. Error messages include remediation steps — executable documentation.

Consumer repos silence warnings with reasons via `.repo-standards.yml`:
```yaml
acknowledged:
  commitlint_config: "uses baked commitlint from image"
```

### Custom semgrep rules

Custom rules beyond what MegaLinter's `auto + p/trailofbits` provides:

- **test-quality**: over-mocking, mock call counts, hardcoded dict assertions
- **sql-safety**: string interpolation in SQL (Python + JS)
- **silent-fallbacks**: empty catches, bare except, fallbacks without comments
- **python-typing**: bare `dict` params/returns (sync + async)
- **shell-complexity**: jq-in-shell nudges toward Python
- **shell-hygiene, compose-security, justfile-safety, yaml-env-vars**

## Key Concepts

**Consumer repos** inherit the baseline via EXTENDS URL in `.mega-linter.yml`. They override with `_CONFIG_FILE` (one line, MegaLinter auto-passes it as CLI flag). Never use `_ARGUMENTS` for config paths — it blocks consumer overrides.

**EXTENDS merges arrays** — consumers must not override array-valued keys containing absolute image paths. Either omit (inherit) or stop using EXTENDS.

**The catalog** (`docs/catalog.md`) is auto-generated from config files by `scripts/generate_catalog.py`. It IS the source of truth — not a doc to maintain.

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
docker run --rm -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards:latest lint PYTHON_RUFF
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
  generate_repo_manifest.py         # Manifest generator for repo standards
  generate_catalog.py               # Auto-generates docs/catalog.md
  megalinter_report_statuses.py     # Posts per-linter commit statuses (Gitea + GitHub)
  blast_radius.py                   # Change impact analysis (blast radius, coupling, CIRank)
  ci/check-drift.sh                 # Generic generated-file drift checker
  ci/check-expiry.py                # Expiry/TTL enforcement for date markers

docs/
  catalog.md                        # GENERATED — full inventory of all checks
  consumer-guide.md                 # Getting started + customization + contributing
  config-decisions.md               # Every decision with rationale
  archive/                          # Historical: migration plan, old architecture decisions

.ci.json                            # Data-driven smoke tests (tool --version + policy tests)
.github/workflows/
  ci.yml                            # Single pipeline: fast-checks → self-lint + build → push
  lint.yml                          # Legacy reusable workflow (being replaced by Docker image)
```

## Contributing new checks

### Where does it live?

| Check type | Files to touch | Auto-detection |
|---|---|---|
| **Repo setup** (file/dep presence) | manifest field in `generate_repo_manifest.py` + `manifest_schema.py` + `policies/repo-standards/*.rego` + `*_test.rego` + `test/test_generate_repo_manifest.py` | Manifest scans repo |
| **Code pattern** (anti-pattern in source) | `semgrep-rules/*.yml` | Semgrep matches patterns |
| **Config content** (compose/YAML validation) | `policies/compose/*.rego` + `*_test.rego` | Conftest parses files |
| **Code quality rule** | `lint-configs-626465/ruff.toml` (add category) | Ruff runs on .py files |
| **New linter tool** | `Dockerfile` (install) + `plugins/*.yml` (descriptor) + `.mega-linter-default.yml` (3 places: ENABLE + DISABLE_ERRORS + PLUGINS) + `.ci.json` (smoke test) | MegaLinter orchestrates |
| **ESLint rule** | `lint-configs-626465/eslint.config.mjs` | ESLint runs on .js/.ts |

### What's automated

- `docs/catalog.md` regenerates via `scripts/hooks/regenerate-catalog` pre-commit hook when source files change
- Pydantic schema in `manifest_schema.py` validates manifest structure — wrong field name is a runtime error
- `conftest verify` in `.ci.json` catches broken Rego policies in Docker build
- `semgrep --validate` in `.ci.json` catches broken semgrep rules in Docker build

### Checklist for adding a new linter tool

1. Install in `Dockerfile` (pip/npm + version pin)
2. Create `plugins/<tool>.megalinter-descriptor.yml`
3. Add to `.mega-linter-default.yml`: `ENABLE_LINTERS` + `DISABLE_ERRORS_LINTERS` (warn tier) + `PLUGINS`
4. Add `<tool> --version` to `.ci.json`
5. Pre-commit runs `generate_catalog.py` automatically
6. Test: `docker build` + entrypoint commands

## Dev workflow — three commands

```bash
just check     # fast local checks via pre-commit (ruff, pytest, semgrep, catalog drift, etc)
just lint      # full MegaLinter suite via Docker image
just verify    # both + rego policy tests
```

`just check` is the single command. CI runs the same pre-commit config.
`just lint` runs the shipped Docker image — verifies what consumers will get.
`just verify` runs everything — use before creating a PR.

Individual checks: `just test` (pytest only), `just test-rego` (Rego unit tests), `just test-semgrep` (rule validation).

## Building the image

```bash
just build                    # docker build
just lint PYTHON_RUFF         # single linter via image
```
