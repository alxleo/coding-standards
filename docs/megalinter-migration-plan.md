# MegaLinter Migration Plan

## Goal

Replace the 400-line custom reusable workflow with a single Docker image that:
- Runs identically everywhere: `docker run`, Gitea CI, GitHub Actions, git hooks
- Auto-detects relevant linters based on file presence (MegaLinter's model)
- Covers both file linters AND centralizable project analyzers
- Produces structured file-based output for CI/agents to consume
- Works on Gitea and GitHub with per-linter commit statuses

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Interface Layer (CI's job, not the image's)     │
│  - Read megalinter-reports/mega-linter-report.json│
│  - Post per-linter commit statuses (Gitea/GitHub)│
│  - Write step summary (GitHub only)              │
│  - Surface file:line:col messages for agents     │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│  Orchestration Layer (thin CI workflow)           │
│  - actions/checkout                              │
│  - docker run ghcr.io/alxleo/coding-standards    │
│  - report-statuses step (reads JSON, posts API)  │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│  Capability Layer (the Docker image)             │
│  - FROM oxsecurity/megalinter-cupcake:v9         │
│  - 91 built-in linters (auto-detect + opt-out)   │
│  - 10+ custom tools as plugins / RUN installs    │
│  - JSON_REPORTER=true for structured output      │
└─────────────────────────────────────────────────┘
```

## Base Image: MegaLinter cupcake v9

**Why cupcake:** Covers 16/26 required tools out of the box. No tools are "in MegaLinter but not cupcake" — larger flavors don't fill any gaps. All 10 gaps are tools MegaLinter doesn't know about.

### Cupcake linters: ENABLED (use as-is)

| Category | Tool | Notes |
|----------|------|-------|
| Shell | shellcheck, shfmt | No overlap, both essential |
| Python | ruff (lint + format) | Replaces flake8, black, isort, most pylint |
| YAML | yamllint | Semantic YAML checks prettier can't do |
| Dockerfile | hadolint | Only option |
| Actions | actionlint | Only option |
| Markdown | markdownlint | Need to verify cli vs cli2 config compat |
| Copy-paste | jscpd | Needs config tuning (486 errors on this repo) |
| Secrets | gitleaks | CI gate. TruffleHog as separate periodic audit |
| Security | semgrep | Only SAST tool — finds code bugs, not just config |
| Formatting | prettier | Gated on package.json presence |
| JS/TS | eslint (JS/TS/JSX/TSX) | Auto-detects |
| Terraform | tflint | Auto-detects |
| Editorconfig | editorconfig-checker | Only option |
| Links | lychee | Link checking |
| Git | git_diff | Harmless |

### Cupcake linters: DISABLED (redundant or wrong for centralized use)

| Tool | Why disabled |
|------|-------------|
| flake8 | 100% superseded by ruff |
| pylint | Needs per-project deps to be useful. Ruff covers generic rules |
| mypy | Type checking is valuable but needs per-project config (see pyright below) |
| pyright | Kept as opt-in — see "Type Checking" section |
| black | 100% superseded by ruff format |
| isort | 100% superseded by ruff I rules |
| checkov | IaC overlap with Trivy. Noisy, slow |
| kics | IaC overlap with Trivy and Checkov |
| grype | Vuln scanning overlap with Trivy |
| syft | No SBOM consumer today |
| secretlint | Strict subset of gitleaks |
| trufflehog | Valuable for audits but too slow/noisy for CI (use as cron job) |
| cspell | Removed — dictionary noise in shell/YAML repos without catching real typos |
| jsonlint | Redundant with check-json + prettier |
| npm-package-json-lint | No universal baseline, highly project-specific |
| markdown-table-formatter | Cosmetic only, conflicts with LLM-generated tables |

### Cupcake linters: EVALUATE

| Tool | Status |
|------|--------|
| v8r (schema validation) | Include with bundled schemas (no runtime network dep) |
| pyright (type checking) | Include in basic mode — catches LLM-generated type bugs. See below |

### Custom additions (baked into image)

| Tool | Install method | Plugin descriptor? | Category |
|------|---------------|-------------------|----------|
| trivy (v0.69.3 PINNED) | Multi-stage COPY, checksum verified | Yes — `cli_lint_mode: project` | Security (vuln + IaC) |
| pyright | `npm install -g pyright` | Yes — `cli_lint_mode: project` | Type checking (Python) |
| commitlint | `npm install -g @commitlint/cli @commitlint/config-conventional` | Yes — `cli_lint_mode: project` | Commit analyzer |
| zizmor | Binary download | Yes — `cli_lint_mode: project` | GHA security |
| dclint | `npm install -g dclint` | Yes (exists in MegaLinter plugin catalog) | Docker Compose linter |
| caddy fmt | Binary download | Yes — `cli_lint_mode: list_of_files`, file pattern `Caddyfile` | Formatter |
| just --fmt | Binary download | Yes — `cli_lint_mode: list_of_files`, file pattern `justfile` | Formatter |
| tsc --noEmit | `npm install -g typescript` | Yes — `cli_lint_mode: project`, gated on `tsconfig.json` | Type checker (JS/TS) |
| knip | `npm install -g knip` | Yes — `cli_lint_mode: project`, needs PRE_COMMANDS npm ci | Dead code detection |
| dependency-cruiser | `npm install -g dependency-cruiser` | Yes — `cli_lint_mode: project`, needs PRE_COMMANDS npm ci | Architecture rules |
| npm audit | Ships with Node | Yes — `cli_lint_mode: project`, gated on `package-lock.json` | Supply chain |
| license-checker | `npm install -g license-checker` | Yes — `cli_lint_mode: project`, gated on `package-lock.json` | License compliance |

### Custom hooks (from current coding-standards)

These run as MegaLinter plugins with `cli_lint_mode: project` or individual
plugin descriptors, replacing BASH_EXEC for per-hook granularity:

- forbid-bare-python
- temp-file-needs-trap
- pin-npm-versions
- block-secret-files / forbid-cruft-files
- shell-hygiene checks

## Configuration Strategy

### Config distribution: baked default + optional EXTENDS override

The image ships with a sensible `.mega-linter.yml` baked in. Consumer repos
work out of the box with zero config. Consumers CAN override by placing their
own `.mega-linter.yml` with `EXTENDS` pointing at a remote baseline, or by
setting individual overrides.

### Blocking policy: two tiers (error / warn)

**Tier 1 — BLOCKS the build (errors):**
gitleaks, semgrep, trivy, pyright, tsc, ruff, shellcheck, eslint, hadolint,
actionlint, commitlint, knip, dependency-cruiser, npm audit, license-checker,
zizmor, caddy fmt, just --fmt

**Tier 2 — WARNS but does not fail (DISABLE_ERRORS_LINTERS):**
prettier (all variants), shfmt, markdownlint, yamllint, jscpd,
editorconfig-checker, stylelint, lychee, v8r, dclint, sqlfluff, ansible-lint,
kubeconform

Consumers can promote/demote via `ENABLE_ERRORS_LINTERS` /
`DISABLE_ERRORS_LINTERS` in their `.mega-linter.yml`.

### Auto-fix: caller-controlled flag

Default: `APPLY_FIXES=none` (check-only, report what's wrong).

To auto-fix: pass `-e APPLY_FIXES=all` to the docker run command.
This is an explicit, intentional action — no surprise file modifications.

```bash
# Check only (default)
docker run --rm -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards

# Auto-fix formatting
docker run --rm -v $PWD:/tmp/lint -e APPLY_FIXES=all ghcr.io/alxleo/coding-standards
```

### Global PRE_COMMANDS (guarded)

```yaml
PRE_COMMANDS:
  - command: "test -f package-lock.json && npm ci --ignore-scripts || true"
    cwd: workspace
    continue_if_failed: true
```

Runs once globally. Non-JS repos skip it (no package-lock.json).
JS linters (knip, dependency-cruiser, tsc) benefit from installed deps.

### Parallel execution

`PARALLEL: true` (default). Linters of the same language group run in
parallel. No config needed.

### Linter activation: allowlist (ENABLE_LINTERS)

Explicit list of 34 linters. New MegaLinter versions don't change what runs.
Consumer repos that need a different set copy and amend the list.

### Reporters

| Reporter | Setting | Why |
|----------|---------|-----|
| Console | true | stdout for agents |
| Text | true | per-linter log files |
| JSON | true (detailed) | our reporting script reads this |
| Markdown Summary | true | GitHub step summary (no-op on Gitea) |
| TAP | **false** | CRITICAL: breaks project-mode linters |
| SARIF | false | no consumer |
| GitHub Status | false | we post statuses ourselves |
| GitHub Comment | false | not needed |
| Config | false | no IDE config generation |
| Updated Sources | false | APPLY_FIXES flag controls |
| File.io | false | never upload externally |
| Email | false | not needed |
| API/Grafana | false | not needed now |

### Performance

- `PARALLEL: true` (default)
- `PRINT_ALPACA: false` — no ASCII art
- `SHOW_ELAPSED_TIME: true` — per-linter timing
- `PRINT_ALL_FILES: false` — noise reduction
- `FLAVOR_SUGGESTIONS: false` — custom flavor
- `SHOW_SKIPPED_LINTERS: false` — noise reduction
- `VALIDATE_ALL_CODEBASE: true` — always lint all files

### File filtering

- `IGNORE_GENERATED_FILES: true` — skip @generated markers
- `IGNORE_GITIGNORED_FILES: true` — respect .gitignore
- Additional excluded dirs: megalinter-reports, .terraform, `__pycache__`, etc.

### Security

- `SECURED_ENV_VARIABLES: [GITEA_TOKEN]`
- POST_COMMANDS for status reporting uses `secured_env: false`
- Default secured list covers TOKEN/PASSWORD/USERNAME patterns

### Linter config files

- `LINTER_RULES_PATH: /opt/coding-standards/configs` (baked into image)
- Consumer repos override specific tools via `<LINTER>_CONFIG_FILE: .foo`

### Full config file

See `.mega-linter-default.yml` in this repo for the complete configuration.

## Output Strategy

### Image produces (capability):
- `megalinter-reports/mega-linter-report.json` — structured per-linter results
  (status, error count, warning count, per-file stdout, elapsed time)
- `megalinter-reports/linters_logs/` — one text log per linter, filename
  encodes pass/fail (e.g., `PYTHON_RUFF-SUCCESS.log`, `BASH_SHELLCHECK-ERROR.log`)
- stdout with `file:line:col: message` format — what agents read
- Exit code 0/1 — universal gate

### CI produces (interface):
- Per-linter commit statuses via Gitea/GitHub API (reads JSON report)
- Step summary table (GitHub only, from JSON report)
- A ~30-line `report-statuses.py` replaces current `report_statuses.py` + `summary.py`

### Agent consumption:
- Agents read raw CI logs (research confirmed no agent consumes SARIF)
- Clean stdout with `file:line:col: message` is the universal format
- Compact JSON summary at end of log for structured extraction
- Noise reduction > format sophistication

## Consumer Repo Experience

### Minimal setup (new repo):

```yaml
# .gitea/workflows/lint.yml (or .github/workflows/lint.yml)
name: Lint
on: [push]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Lint
        run: |
          docker run --rm \
            -v $PWD:/tmp/lint \
            -e JSON_REPORTER=true \
            ghcr.io/alxleo/coding-standards:latest
      - name: Report statuses
        if: always()
        run: |
          # thin script reads megalinter-reports/mega-linter-report.json
          # posts per-linter commit statuses
          python3 <(curl -s https://raw.githubusercontent.com/alxleo/coding-standards/main/scripts/report-statuses.py) \
            megalinter-reports/mega-linter-report.json
```

Image auto-detects which linters apply based on files present. Zero config
for standard repos.

### Customization (existing repo):

```yaml
# .mega-linter.yml in repo root
DISABLE_LINTERS:
  - TERRAFORM_TFLINT      # no terraform in this repo
  - REPOSITORY_TRIVY       # handled separately

ENABLE_LINTERS:            # opt-in to non-default tools
  - REPOSITORY_COMMITLINT

PRE_COMMANDS:
  - command: npm ci        # needed for knip, dep-cruiser, tsc
    cwd: workspace
    continue_if_failed: true

# Tool-specific config overrides
PYTHON_RUFF_CONFIG_FILE: ruff.toml
YAML_YAMLLINT_CONFIG_FILE: .yamllint.yml
```

### Skip mechanism:
- `DISABLE_LINTERS` for individual tools
- `DISABLE` for entire categories (e.g., `PYTHON`, `JAVASCRIPT`)
- `SKIP` env var for backward compat with current `.coding-standards.yml`

## Deliverables

### Phase 1: Image + Core (this repo)

1. **Dockerfile** — `FROM oxsecurity/megalinter-cupcake:v9` + custom tool installs
2. **Plugin descriptors** — `.megalinter-descriptor.yml` files for each custom tool
3. **Default `.mega-linter.yml`** — baseline config baked into image
4. **`scripts/report-statuses.py`** — reads JSON report, posts Gitea/GitHub statuses
5. **CI workflow** — builds and pushes image to GHCR on tag
6. **Self-test** — CI runs the image against this repo

### Phase 2: Consumer Rollout

7. **home-network** — replace 180-line bespoke lint.yml with 3-step workflow
8. **platform** — replace experiment/megalinter branch with production setup
9. **github-standards** — update sync targets
10. **Example workflow** — update `examples/lint.yml`

### Phase 3: Polish

11. **Custom hooks migration** — convert current pre-commit hooks to MegaLinter plugins
12. **Config distribution** — evaluate whether `.mega-linter.yml` EXTENDS replaces `apply-configs.sh`
13. **Local development** — `just lint` recipe that runs the same image
14. **Documentation** — update README, CLAUDE.md, architecture-decisions.md

## Multi-Tier Strategy

The Docker image is the primary CI solution, but not the only tier:

1. **MegaLinter image** (primary) — CI on Gitea/GitHub. Full coverage, structured output.
2. **pre-commit** (lightweight) — for repos without CI, local hooks, or weaker-model
   agent contexts where catching bad code early matters. Already works with
   `pass_filenames: false` for project analyzers.
3. **SonarQube CE** (follow-up) — deeper analysis: cross-file taint tracking, quality
   gates, complexity metrics. Adds what MegaLinter can't do natively. Separate concern.

## Multi-Arch Strategy

Standard MegaLinter images are amd64-only. MegaLinter v9.4.0's Custom Flavor
Builder supports multi-arch builds (`linux/amd64,linux/arm64`).

All tools we use are arm64-compatible. The amd64-only holdouts in MegaLinter
are niche tools we don't need (Salesforce, Azure, Clojure, LaTeX).

**Approach:** Use Custom Flavor Builder to generate a multi-arch Dockerfile
that includes only our linters + custom tools. Set
`platform: "linux/amd64,linux/arm64"` in the build workflow.

- **linux/amd64** — Gitea runners, GitHub Actions
- **linux/arm64** — local Mac development, arm64 runners

## Supply Chain Security

**Pin everything by digest/SHA. Automate updates with Renovate.**

The Trivy supply chain compromise (March 2026, v0.69.4-6 malicious) proved
that semver tags are not trustworthy. SHA pinning is the only guarantee.

### What gets pinned:
- **Docker base image**: `FROM oxsecurity/megalinter-cupcake:v9@sha256:...`
- **Multi-stage COPY sources**: `COPY --from=ghcr.io/aquasecurity/trivy:0.69.3@sha256:...`
- **Binary downloads**: checksum verification on every curl/wget install
- **npm packages**: exact versions (`@commitlint/cli@19.7.1`), not ranges
- **GitHub Actions** (in consumer workflows): commit SHA, not tag

### Automated maintenance:
- Renovate watches Dockerfile, package.json, workflow files
- Auto-creates PRs with updated digests/checksums on new releases
- CI tests the update before merge
- Pinning + Renovate = security without maintenance burden

## Open Questions

- [ ] markdownlint-cli vs markdownlint-cli2 — does the config format difference matter?
- [x] ~~MegaLinter's cupcake flavor includes Grype/Checkov for security scanning — overlap with trivy?~~ **RESOLVED: Disable checkov, kics, grype, syft. Keep trivy + semgrep.**
- [ ] Does `PRE_COMMANDS: npm ci` work reliably across different Node project shapes?
- [ ] Can MegaLinter's `EXTENDS` fetch a remote `.mega-linter.yml` for centralized defaults?
- [ ] Image build time — how long to build cupcake + custom tools? Acceptable for CI-on-push?
- [ ] MegaLinter version pinning strategy — pin to v9.x minor, or track latest?
- [ ] v8r schema bundling — how to download schemas at build time and configure v8r to use local copies?
- [ ] Trivy supply chain incident — monitor for clean v0.70+ release. Fallback: Grype + Checkov
- [ ] pyright basic mode — does it produce useful results on unannotated code without deps? (researching)

## What Gets Retired

Once Phase 2 is complete, these become obsolete:
- `.github/workflows/lint.yml` (400-line reusable workflow)
- `scripts/ci/groups.conf`, `lint-run.sh`, `summary.py` (custom orchestration)
- `scripts/ci/run-{hygiene,cruft,actions,python}.sh` (group runners)
- `scripts/ci/install-tool.sh` (tool installer — Docker image replaces this)
- `scripts/ci/apply-configs.sh` (config distribution — MegaLinter's config mechanism replaces this)
- `action.yml` (composite action)

What stays:
- `lint-configs-626465/` — linter config files (referenced by MegaLinter via `*_CONFIG_FILE` env vars)
- `scripts/hooks/` — custom hook scripts (now invoked by MegaLinter plugins instead of pre-commit)
- `scripts/report-statuses.py` — rewritten to read MegaLinter JSON
- `test/` — updated for new architecture
