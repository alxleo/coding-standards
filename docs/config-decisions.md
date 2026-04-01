# Config Decisions Log

Decisions made 2026-03-29. Revisit if assumptions change.

## Architecture

- **MegaLinter cupcake base** — covers 18/34 tools. No larger flavor fills gaps.
- **Custom Docker image** — FROM cupcake + 16 custom tools as plugins/installs.
- **Multi-arch** via Custom Flavor Builder — amd64 (Gitea/GHA) + arm64 (Mac). All our tools are arm64-compatible.
- **Reporting separated from image** — image lints + writes JSON. CI posts Gitea/GitHub statuses. Kills the "no Gitea reporter" blocker.
- **Repo home**: this repo (coding-standards). Dockerfile + plugins + configs all here.

## Linter Selection

### Python: ruff only (+ pyright standard)

- flake8/black/isort: 100% superseded by ruff.
- pylint: needs per-project deps. Generic rules already in ruff.
- mypy: skips unannotated functions by default. Wrong for LLM code.
- **pyright standard mode**: catches hallucinated APIs, wrong args, type bugs. Works without deps for stdlib + typeshed (~600 packages). reportMissingImports: warning.
- ty (Astral): 15% conformance. Revisit H2 2026.

### Security: trivy + semgrep only

- checkov/kics: IaC overlap with trivy. Noisy, slow.
- grype: vuln overlap with trivy.
- syft: no SBOM consumer.
- trivy pinned to v0.69.3 (supply chain compromise in v0.69.4-6).

### Secrets: gitleaks only in CI

- secretlint: strict subset of gitleaks.
- trufflehog: valuable for `--only-verified` audits. Use as periodic cron, not CI.

### Config files: keep existing stack

- jsonlint: redundant with check-json + prettier.
- v8r: include with bundled schemas. Soft-fail (endpoints go down).
- npm-package-json-lint: no universal baseline.
- markdown-table-formatter: cosmetic, conflicts with LLM tables.
- markdownlint replaced by rumdl: MegaLinter ships markdownlint-cli (v1) which can't parse cli2 config format, and cli2 silently treats `-c` as a glob. rumdl reads existing `.markdownlint-cli2.yaml` natively, has `--config` that works with `_CONFIG_FILE`, and is 23x faster (Rust).

### Spelling: codespell (warn tier)

- codespell over typos-cli: 29 findings vs 139 on same codebase (typos flags regex substrings, product names, base64).
- codespell over cspell: far less configuration needed. cspell requires comprehensive dictionary setup.
- Warn tier: false positives on domain terms (tool names, acronyms) would unfairly gate builds. Consumer repos promote to error if desired.
- Already in cupcake base image — zero install cost.

### Ruff categories: PIE, ISC, A, PGH, RSE

- PIE: unnecessary spread, reimported names, no-op pass statements.
- ISC: implicit string concatenation — catches accidental tuple-in-list. ISC001 excluded (conflicts with ruff formatter).
- A: builtin shadowing (list, dict, type, id). LLMs do `id = container["Id"]` constantly.
- PGH: blanket `# type: ignore` / `# noqa` without codes. Prevents suppression creep.
- RSE: unnecessary parens in raise.
- ANN not added: redundant with pyright. pyright infers+validates types; ANN only checks annotations exist.

### Semgrep: bare-dict parameter/return rule

- No existing tool flags `def foo(config: dict)`. Custom semgrep rule catches bare `dict` params and returns.
- Prevents new instances of anonymous-dict patterns that lose all type information.
- WARNING severity (doesn't block, guides toward TypedDict or dict[K, V]).

### EXTENDS merges arrays (consumer gotcha)

- MegaLinter's EXTENDS mechanism **merges** arrays instead of replacing them.
- A consumer setting `REPOSITORY_SEMGREP_RULESETS: [auto]` gets `[auto, p/trailofbits, /opt/.../semgrep-rules/, auto]` — duplicated and with corrupted relative paths.
- Consumer repos should NOT override array-valued keys containing absolute image paths when using EXTENDS. Either omit (inherit baseline as-is) or stop using EXTENDS and copy the baseline config locally.

### Added from audit

- stylelint (CSS), sqlfluff (SQL), ansible-lint, kubeconform (K8s). All self-selecting.

### ESLint baseline: unicorn + security + sonarjs

- eslint-plugin-unicorn: filename conventions (kebab-case), modernization, best practices. filename-case rule catches non-importable Python modules.
- eslint-plugin-security: eval injection, unsafe regex, timing attacks, prototype pollution.
- eslint-plugin-sonarjs: cognitive complexity, duplicate strings, identical functions, collapsible if.
- eslint-plugin-jest: already in cupcake image. Consumer adds to their config for expect-expect, no-disabled-tests.
- Biome not adopted: faster but shallower ecosystem. ESLint already in image with deeper plugin support.
- Baseline config baked at `/opt/coding-standards/configs/eslint.config.mjs`. Consumers override with their own eslint config.

### Filename conventions: Python snake_case enforced

- Hyphens in Python filenames prevent importing (old `generate-repo-manifest.py` couldn't be imported — renamed to snake_case).
- JS/TS: eslint-plugin-unicorn enforces kebab-case or PascalCase.
- Python: no existing linter checks filenames. Added as repo-standard manifest check.
- Shell: no enforcement (not imported, convention only).

### Watch list

- oxlint: when v1.0 + type-aware linting stabilizes.
- biome: when adoption solidifies as ESLint + Prettier replacement.

## Config Decisions

### Activation: allowlist (ENABLE_LINTERS)

- Prevents surprise linters on MegaLinter version bumps.

### Blocking: two tiers

- Error: security + types + syntax + correctness tools.
- Warn: formatters + style + links + schema + new additions.
- No "info" tier. If not worth acting on, don't run it.

### Auto-fix: caller flag

- Default: APPLY_FIXES=none (check only).
- `-e APPLY_FIXES=all` to auto-fix. Explicit, no surprises.

### Config paths: `_CONFIG_FILE` preferred, PRE_COMMANDS for auto-discovery tools

- Most linters: `_CONFIG_FILE` pointing to baked config. MegaLinter auto-passes it via `cli_config_arg_name`.
- Consumer repos override via `<LINTER>_CONFIG_FILE: myconfig.toml` — one line, works correctly.
- Exceptions (tools where `_CONFIG_FILE` injects the wrong flag):
  - **JSON v8r**: built-in descriptor's `-c` means `--catalogs`, not config. Config copied to workspace via PRE_COMMANDS; cosmiconfig discovers it.
  - **shellcheck**: built-in descriptor inherits default `-c` which shellcheck has never accepted (uses `--rcfile` since v0.10, auto-discovery since v0.7). Config copied to workspace via PRE_COMMANDS.
  - **shfmt**: reads `.editorconfig` from file's directory tree. Symlinked at repo root, copied to workspace via PRE_COMMANDS.
  - **editorconfig-checker**: built-in `-config` expects `.ecrc` (tool JSON config), not `.editorconfig`. Auto-discovers `.editorconfig` from workspace.
- PRE_COMMANDS copies use `test ! -f` guards — consumer files at workspace root take precedence over baked defaults.

### Config distribution: baked + override

- Image ships .mega-linter.yml + linter configs. Works offline.
- Consumer repos override via own .mega-linter.yml or per-linter _CONFIG_FILE.
- LINTER_RULES_PATH points inside image (/opt/coding-standards/configs).
- No EXTENDS / CONFIG_PROPERTIES_TO_APPEND by default. Replace > merge (simpler).

### Reporters

- TAP: OFF. Breaks project-mode linters (trivy, commitlint, knip).
- JSON: ON (detailed). Our reporting script reads this.
- GitHub Status/Comment: OFF. We post statuses ourselves (Gitea compat).
- Markdown Summary: ON. GitHub step summary, harmless no-op on Gitea.

### Performance

- VALIDATE_ALL_CODEBASE: true (always all files, simplicity over speed).
- PARALLEL: true. PRINT_ALPACA: false. FLAVOR_SUGGESTIONS: false.
- Output sanitization: kept ON (safety > speed).

### Security

- SECURED_ENV_VARIABLES: GITEA_TOKEN added. Linters never see it.
- POST_COMMANDS status reporter uses secured_env: false.

### PRE_COMMANDS

- git safe.directory + autocrlf fix (Docker UID mismatch).
- Copy baked configs to workspace root for tools that auto-discover (v8r, shellcheck, shfmt, editorconfig-checker, codespell, ls-lint). Uses `cp` not symlinks (prettier rejects symlinks). NOTE: MegaLinter checks `active_only_if_file_found` BEFORE PRE_COMMANDS, so these copies provide config, not activation. commitlint excluded — needs git history (HEAD~1) which Docker-mounted workspaces lack.
- npm ci guard (runs only if package-lock.json exists).

### Self-lint: MEGALINTER_CONFIG override

- CI self-lint uses `MEGALINTER_CONFIG=/opt/coding-standards/.mega-linter-default.yml` — the baked image config, not the workspace `.mega-linter.yml` (which uses EXTENDS from a stale main branch).
- This ensures the self-lint validates the config that consumers will actually get.

### `_CONFIG_FILE` must be relative (bare filenames)

- MegaLinter concatenates `LINTER_RULES_PATH + _CONFIG_FILE`. Absolute paths break silently.
- Enforced by `check-megalinter-config-paths` pre-commit hook.
- All `_CONFIG_FILE` values are bare filenames: `ruff.toml`, `.hadolint.yaml`, etc.

### Supply chain

- SHA-pin everything: Docker images by digest, binaries by checksum, npm by exact version.
- Renovate automates version bump PRs.

### Multi-tier strategy

1. MegaLinter image (primary) — CI on Gitea/GitHub.
2. pre-commit (lightweight) — repos without CI, local hooks.
3. SonarQube CE (follow-up) — cross-file taint, quality gates.

### Ruff per-file-ignores for test/CI code

- Security rules (S prefix) produce structural false positives in test and CI code.
- S101 (assert): pytest requires assert. S108 (/tmp): CI runs in ephemeral containers. S310 (urllib): URLs from CI env vars. S603/S607 (subprocess): CI scripts call tools.
- Fix: per-file-ignores in ruff.toml, not inline noqa comments. Tests and scripts get exemptions; application code does not.
- Pattern: security rules are valuable for application code, exempt infrastructure/test code at the config level.

### Performance optimizations applied

- jscpd → PMD-CPD: 177s → 5s (Java vs Node.js, Karp-Rabin matching)
- Trivy DB pre-cached at build time: 12.6s → 3s (--skip-db-update at runtime)
- Semgrep: local rules backfired (10x slower). Kept --config auto (server-side curation worth the 10s download)
- v8r schema caching: pending (11+12s savings expected)
- Wall clock: 3+ min → 31s under emulation, estimated 15-20s native amd64

### Monorepo scoping

FILTER_REGEX_INCLUDE/EXCLUDE only works for file-mode linters (shellcheck, ruff, yamllint).
Project-mode linters (trivy, semgrep, gitleaks, conftest, knip, etc.) ignore it entirely.
For monorepos like home-network: single MegaLinter run + tool-native scoping:

- ruff: per-file-ignores in ruff.toml
- ansible-lint: exclude_paths in .ansible-lint
- tflint: auto-scoped via file presence (.tf)
- hadolint: auto-scoped via file presence (Dockerfile)
Matrix strategy (parallel per-directory runs) is possible but adds CI complexity.

### Graduated rollout for new rules

New rules follow the Clippy/Biome pattern:

- Rules are enabled in the config from day one (new code must comply).
- Existing code uses `ruff --add-noqa` to generate inline suppressions.
- Each suppression is a visible TODO, not hidden tech debt.
- Over time, clean up suppressions — the noqa count is a health metric.
- Preferred over warn-tier demotion because it enforces quality on NEW code immediately.

Migration recipe in consumer-guide.md: `ruff check --fix && ruff check --add-noqa`.

### Skipped

- LLM Advisor: the agent consuming output IS an LLM. Skip.
- Grafana/API reporter: not needed now.
- SARIF: no consumer (agents read raw logs).
