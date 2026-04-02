# coding-standards

A Docker image that acts as a seed — drop it into any repo's CI and it tells you what to set up, catches bugs, enforces security, and improves over time as new checks are added.

Built on MegaLinter. Runs identically on Gitea Actions and GitHub Actions.

## Architecture: Three Layers

### 1. Enforcement (linters + security)

Two tiers — error (blocks build) and warn (reports only). See `docs/catalog.md` for the full inventory.

### 2. Structural validation (conftest/Rego policies)

- `policies/compose/` — Docker Compose: healthchecks, resource limits, image pinning
- `policies/repo-standards/` — Repo setup: CI config, pre-commit hooks, dependencies, naming

### 3. Change impact analysis

`scripts/blast_radius.py` — answers "how hard is it to make a correct change?"
- Blast radius (filename reference count)
- Temporal coupling (Jaccard on git co-changes)
- CIRank (PageRank weighted by co-change)
- Naming entropy (convention consistency per directory)

Usage: `docker run ... blast-radius --pr FILE [FILE ...]`

## Dev workflow

```bash
just check       # all checks — identical to CI (35 pre-commit hooks)
just lint         # full MegaLinter via Docker (branch configs mounted)
just verify       # both + rego tests
just show-config  # which config each linter uses + shadow detection
just measure      # blast radius / coupling / entropy analysis
```

`just check` is THE command. CI calls it. No duplication.

## Key rules

**`_CONFIG_FILE` must be bare filenames** — `ruff.toml` not `/opt/.../ruff.toml`. MegaLinter concatenates `workspace + _CONFIG_FILE`; absolute paths break silently. Enforced by `check-megalinter-config-paths` hook.

**Every pre-commit hook must have `--config`** — explicit config flags, no auto-discovery. Enforced by `check-config-flags` hook.

**CI calls `just check`, not inline linting** — one source of truth. Enforced by `ci_delegates_to_runner` repo-standard policy.

**Merge, don't rebase** — squash-merge on GitHub makes branch history irrelevant. Rebase requires force-push which breaks parallel agents.

## Repository layout

```
Dockerfile                          # MegaLinter cupcake + custom tools
.mega-linter-default.yml            # Baseline config (inherited via EXTENDS)
docker-action/action.yml            # Composite action for consumer CI

lint-configs/                       # Baked linter configs
  .pre-commit-config.yaml           # Pre-commit hooks (authoritative config)
  ruff.toml, .yamllint, .prettierrc, eslint.config.mjs, etc.

plugins/                            # MegaLinter plugin descriptors
policies/
  compose/                          # Compose file validation
  repo-standards/                   # Repo setup validation (44 Rego tests)

semgrep-rules/                      # Custom rules (silent-fallbacks, typing, etc.)

scripts/
  blast_radius.py                   # Change impact analysis (6 algorithms, 93 tests)
  show_config.py                    # Config observability (which config each linter uses)
  generate_repo_manifest.py         # Manifest generator for repo standards
  generate_catalog.py               # Auto-generates docs/catalog.md
  megalinter_report_statuses.py     # Per-linter commit statuses (Gitea + GitHub)
  hooks/                            # Pre-commit validation hooks
    check-config-flags              # Every linter hook has --config
    check-hook-deps                 # Pytest hook has all dependencies
    check-ci-json-coverage          # Every Dockerfile tool has a smoke test
    check-megalinter-config-paths   # _CONFIG_FILE values are relative
    regenerate-catalog              # Auto-regen on config changes
    shell-hygiene                   # Bare python, mktemp cleanup, npx pinning

docs/
  catalog.md                        # GENERATED — full check inventory
  change-impact-techniques.md       # Algorithm registry (6 implemented, 4 planned)
  consumer-guide.md                 # Getting started + customization
  config-decisions.md               # Every decision with rationale

.github/workflows/
  ci.yml                            # Pipeline: fast-checks → self-lint + build → push
  scheduled.yml                     # Weekly: rebuild + trivy + dive + action updates
  gate.yml                          # Branch protection
  release.yml                       # Auto-release v1.x.y on CI success
```

## Contributing new checks

| Check type | Files to touch |
|---|---|
| **Repo setup** | `generate_repo_manifest.py` + `manifest_schema.py` + `policies/repo-standards/*.rego` + `*_test.rego` + `test/` |
| **Code pattern** | `semgrep-rules/*.yml` |
| **Config validation** | `policies/compose/*.rego` + `*_test.rego` |
| **Code quality** | `lint-configs/ruff.toml` |
| **New linter** | `Dockerfile` + `plugins/*.yml` + `.mega-linter-default.yml` (3 places) + `.ci.json` |

### New linter checklist

1. Install in `Dockerfile` (pip/npm + version pin)
2. Create `plugins/<tool>.megalinter-descriptor.yml`
3. Add to `.mega-linter-default.yml`: `ENABLE_LINTERS` + `DISABLE_ERRORS_LINTERS` + `PLUGINS`
4. Add `_CONFIG_FILE: <filename>` (bare filename, resolved via `LINTER_RULES_PATH`)
5. Add `<tool> --version` to `.ci.json`
6. Pre-commit regenerates catalog automatically
7. `just build && just lint <LINTER>` to verify
