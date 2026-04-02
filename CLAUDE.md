# coding-standards

Docker image: `python:3.13-alpine` + MegaLinter engine + linters. Multi-arch (amd64 + arm64). Zero-config for consumers.

## How it works

Image bakes: MegaLinter engine, linter binaries, configs, semgrep rules, conftest policies, help docs, templates.

Consumer adds a CI workflow → image runs → reports findings. No `.mega-linter.yml` needed (baked default used when absent).

Entrypoint handles: zero-config fallback, EXTENDS URL rewrite to local path, consumer `.semgrep/` auto-discovery, workspace ownership cleanup.

## Dev commands

```bash
just check       # pre-commit hooks — THE gate (CI calls this)
just build       # docker build locally
just lint        # full MegaLinter via Docker (mounts branch configs)
just verify      # check + lint + rego tests
```

## Structural invariants (enforced by pre-commit)

7 cross-validation checks run on every commit via `scripts/hooks/check-image-integrity`:

1. Every `ENABLE_LINTERS` entry has an installed binary (Dockerfile)
2. Every `DISABLE_ERRORS_LINTERS` entry is in `ENABLE_LINTERS`
3. Every `_CONFIG_FILE` value exists in `lint-configs/`
4. Every file in `lint-configs/` is referenced by `_CONFIG_FILE` or `_ARGUMENTS`
5. Every Dockerfile COPY source is in CI `hashFiles()` expression
6. Every binary download has amd64 + arm64 SHA256 checksums
7. Every linter category has a help doc in `docs/help/`

If you add a tool and forget a step, the hook tells you what's missing.

## Adding a new linter

Touch these files — the integrity hook validates completeness:

1. **Dockerfile** — install via pip, npm, or binary download
   - Binary: add `TOOL_VERSION`, `TOOL_SHA256_amd64`, `TOOL_SHA256_arm64`
   - Look up real checksums from GitHub release pages, never guess
   - Use `TARGETARCH` for download URL
2. **plugins/\<tool\>.megalinter-descriptor.yml** — define `name`, `cli_executable`, `cli_lint_mode`, `cli_lint_extra_args`
3. **.mega-linter-default.yml** — add to `ENABLE_LINTERS` + `DISABLE_ERRORS_LINTERS` (warn tier for new tools) + `PLUGINS`
4. **lint-configs/\<config\>** — baked config file (if tool needs one)
5. **.mega-linter-default.yml** — add `_CONFIG_FILE: <bare-filename>` (resolved via `LINTER_RULES_PATH`)
6. **.ci.json** — add `"<tool> --version"` smoke test
7. **docs/help/** — ensure the linter's category has a help topic
8. `just build && just lint` to verify

## Adding a semgrep rule

1. Add to `semgrep-rules/<category>.yml` with `id: coding-standards.<rule-name>`
2. `just check` validates rule syntax automatically
3. Catalog regenerates on commit (pre-commit hook)

## Adding a conftest policy

1. Add `.rego` file to `policies/repo-standards/` or `policies/compose/`
2. Add `*_test.rego` with unit tests
3. `conftest verify -p policies/<dir>/` to validate
4. If repo-standards: update `scripts/generate_repo_manifest.py` with the data field

## Key constraints

- **`_CONFIG_FILE` must be bare filenames** — `ruff.toml` not `/opt/.../ruff.toml`. MegaLinter concatenates `LINTER_RULES_PATH + _CONFIG_FILE`. Enforced by `check-megalinter-config-paths`.
- **Binary checksums: both architectures** — every `curl` download needs `_SHA256_amd64` and `_SHA256_arm64`. PMD is exempt (Java, arch-agnostic). Enforced by integrity hook.
- **Semgrep rule IDs: `coding-standards.` prefix** — ensures predictable `--exclude-rule` for consumers.
- **No workspace root pollution** — baked configs go to `.mega-linter-config/` via PRE_COMMANDS. Exceptions: `.editorconfig` (spec requires root), `.v8rrc.yml` (symlink for cosmiconfig).
- **Consumer files are read-only** — never `sed -i` or modify mounted workspace files. Use temp copies.

## Repository layout

```
Dockerfile                          # Alpine base + all tool installs (multi-arch)
.mega-linter-default.yml            # Baseline config (baked, zero-config default)
docker-action/action.yml            # Composite action for consumer CI
consumer.just                       # Consumer justfile (thin wiring, ~50 lines)

lint-configs/                       # Baked linter configs (bare filenames)
plugins/                            # MegaLinter plugin descriptors (22 custom tools)
semgrep-rules/                      # Custom semgrep rules (coding-standards.* prefix)
policies/
  compose/                          # Compose file validation (Rego)
  repo-standards/                   # Repo setup validation (Rego)
  image-integrity/                  # Self-validation policies (Rego)

docs/help/                          # Progressive disclosure help (13 markdown files)
templates/                          # CI workflow + gitignore templates for cs-init

scripts/
  entrypoint.sh                     # Command router + config resolution
  generate_image_manifest.py        # Cross-validation data for integrity hook
  generate_repo_manifest.py         # Consumer repo data for repo-standards
  show_catalog.py                   # Runtime catalog renderer (no generated file)
  extract_linter_timings.py         # Parse MegaLinter report for perf data
  download-schemas.sh               # v8r schemas (build-time)
  download-semgrep-rules.sh         # Cached rulesets as JSON (build-time)
  hooks/
    check-image-integrity           # 7 cross-validation invariants (Python)
    check-ci-json-coverage          # Every Dockerfile tool has a smoke test
    check-config-flags              # Every pre-commit hook has --config
    check-megalinter-config-paths   # _CONFIG_FILE values are bare filenames
    check-hook-deps                 # Pytest hook has all dependencies

.github/workflows/
  ci.yml                            # fast-checks → build (with context-hash skip) → push
  cache-cleanup.yml                 # Delete branch caches on PR close
  scheduled.yml                     # Weekly: rebuild + trivy + dive + cache prune
  release.yml                       # Auto-release on CI success
```
