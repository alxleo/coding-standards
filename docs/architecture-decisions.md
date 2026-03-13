# Architecture Decisions & Future Options

## Current Architecture

Data-driven reusable GitHub Actions workflow. Key design:

- `groups.conf` — single source of truth for linter group metadata
- `lint-run.sh` — wraps each lint step, writes `.outcome` files
- `summary.py` / `report_statuses.py` — iterate `groups.conf` + `.outcome` files (Python, stdlib only)
- `lint_helpers.py` — shared parsing and error extraction (replaces `lib/common.sh`)
- `install-tool.sh` — shared script for pinned binary tool installation
- `apply-configs.sh` — config application (used by both `lint.yml` and `action.yml`)

Adding a new linter group: add a step in `lint.yml` + a line in `groups.conf`.

### Config override strategy

Two tiers based on tool capability:

1. **Extends-capable tools** (yamllint, gitleaks, markdownlint, commitlint): Baseline configs live as `.baseline` files. Consumer specifies an override file in `.coding-standards.yml` that uses the tool's native extends/inherit syntax to chain back to the baseline. `apply-configs.sh` copies the consumer's file into the active config path.

2. **Non-extends tools** (hadolint, jscpd, prettier, shellcheck, editorconfig): Full file replacement. Consumer drops their config at repo root; `apply-configs.sh` copies it into the config directory.

Hook scripts run directly from `.coding-standards/scripts/hooks/` — no copy into the consumer workspace.

## Evaluated Alternatives

### MegaLinter (oxsecurity/megalinter)

**What:** Comprehensive meta-linter (134 linters in `all` flavor, 19 flavor variants) shipped as a Docker image. Python orchestration layer invokes linters directly — independent of pre-commit.

#### Feature coverage mapping

| coding-standards feature | MegaLinter equivalent | Gap? |
|---|---|---|
| yamllint, shellcheck, actionlint, markdownlint, jscpd | Built-in linters (same tools) | No |
| ruff (Python lint + format) | `PYTHON_RUFF` | No |
| gitleaks | `CREDENTIALS_GITLEAKS` | No |
| Trivy (IaC + deps) | `REPOSITORY_TRIVY` | No |
| Semgrep (SAST) | `REPOSITORY_SEMGREP` | No |
| commitlint | Not included | **Yes** — needs `PRE_COMMANDS` or plugin |
| `just --fmt` | Not included | **Yes** — no `just` descriptor exists |
| pre-commit hygiene hooks (check-merge-conflict, check-added-large-files, detect-private-key, end-of-file-fixer, etc.) | Partial overlap via `REPOSITORY_CHECKOV`, `CREDENTIALS_SECRETLINT` | **Yes** — no direct equivalents for most |
| Custom hooks (forbid-bare-python, temp-file-needs-trap, pin-npm-versions) | `BASH_EXEC` (runs scripts) — but single linter, not per-hook | **Yes** — loses per-hook granularity |
| Secret-file blocking (block-secret-files, forbid-cruft-files) | No equivalent (gitleaks scans content, not filenames) | **Yes** |
| Per-group commit statuses | `GITHUB_STATUS_REPORTER: true` — posts per-linter (e.g., `PYTHON_RUFF`), not per-group | Partial — more granular but different grouping |
| Gitea commit statuses | No Gitea reporter — `GitHubStatusReporter` is GitHub-only | **Yes — blocker** |
| Centralized config distribution | `EXTENDS` for `.mega-linter.yml` only — does **not** distribute individual linter configs (`.yamllint`, `.ruff.toml`, etc.) | **Yes** |
| Consumer config overrides | `<LINTER>_CONFIG_FILE`, `LINTER_RULES_PATH` (but see #4254) | Partial — broken for workspace-root overrides |
| Skip mechanism | `DISABLE` / `DISABLE_LINTERS` / `DISABLE_ERRORS_LINTERS` — per-linter, not per-group | No — actually more granular |

#### Custom linter options in MegaLinter

1. **Plugin system**: Create a `.megalinter-descriptor.yml` with `descriptor_id`, `file_extensions`, `linters[]`, and `install` instructions. Load via:

   ```yaml
   PLUGINS:
     - https://raw.githubusercontent.com/org/repo/.../my.megalinter-descriptor.yml
   ```

   URL path must contain `**/mega-linter-plugin-**/`. Each plugin linter gets its own status. More structured than `language: system` but higher effort to create.

2. **`PRE_COMMANDS` / `POST_COMMANDS`**: Run arbitrary shell commands before/after linters. Not treated as linters — no individual status, no reporting. Setup/teardown only.

3. **`BASH_EXEC`**: Runs custom scripts, but as a single linter. All scripts report under one status.

#### Docker image sizes

| Flavor | Linters | Compressed size |
|---|---|---|
| `all` | 134 | ~3.4 GB |
| `ci_light` | 22 | ~0.7 GB |
| `security` | 25 | ~0.8 GB |
| `cupcake` | 91 | ~2.0 GB |
| Language-specific (python, javascript, etc.) | 50-68 | ~1.0 GB |

Current workflow installs ~50 MB of cached binaries total.

#### Known issues relevant to this project

- **#4254**: `LINTER_RULES_PATH` ignores workspace-root config files. If a central config directory is set, consumer repos cannot override individual linter configs by placing them in the workspace root. Workaround: set `<LINTER>_CONFIG_FILE: LINTER_DEFAULT` per linter.
- **#2894**: `LINTER_RULES_PATH` pointing to a non-root directory causes some linters (proselint, vale) to be skipped entirely.
- **#2371**: Recursive `EXTENDS` (config A extends B extends C) does not work properly when mixing remote and local references.

#### Verdict

**Partial alternative, not a superset.** Covers ~70% of the feature surface out of the box. Three blockers:

1. **No Gitea status reporter** — hard requirement for this project
2. **No centralized config distribution** — `EXTENDS` only handles `.mega-linter.yml`, not individual linter config files. Would still need `apply-configs.sh` or equivalent.
3. **Custom hooks lose granularity** — `BASH_EXEC` is all-or-nothing; plugin system is viable but high-effort

**When to revisit:**

- MegaLinter adds a generic/Gitea status reporter
- Gitea support becomes optional for this project
- Custom hooks are absorbed into standard linters (unlikely)

**Current role:** Local CLI use via `npx mega-linter-runner --flavor ci_light` (see `lint-configs-626465/.mega-linter.yml`). This provides a fast local scan with standard linters only — complementary to CI, not a replacement.

### super-linter

**What:** GitHub's official meta-linter action.

**Cons vs current approach:**

- No per-linter commit statuses (single pass/fail only)
- `VALIDATE_*` env vars less flexible than `.coding-standards.yml`
- No Gitea support for advanced features

**Verdict:** Poor fit — no per-group statuses is a dealbreaker.

### pre-commit.ci

**Cons:**

- `language: system` hooks won't run (sandboxed Docker)
- Single pass/fail status only
- No Gitea support
- No centralized config injection

**Verdict:** Not viable for this use case.

### trunk.io (Trunk Check)

**Cons:**

- No per-group commit statuses
- No Gitea integration
- No centralized config distribution
- Web app deprecated (July 2025)
- Hold-the-line approach is a different philosophy

**Verdict:** Not a good fit.

## Future Option: Matrix Strategy

The most promising simplification path for the current architecture.

### How It Would Work

1. A `setup` job reads `groups.json`, filters by skip list + file presence, outputs JSON
2. A `lint` matrix job fans out — one job per group, running in parallel
3. GitHub natively shows each matrix job as a separate check

```yaml
jobs:
  setup:
    runs-on: ubuntu-latest
    outputs:
      groups: ${{ steps.detect.outputs.groups }}
    steps:
      - id: detect
        run: |
          echo "groups=$(jq -c '...' groups.json)" >> "$GITHUB_OUTPUT"

  lint:
    needs: setup
    strategy:
      fail-fast: false
      matrix:
        group: ${{ fromJSON(needs.setup.outputs.groups) }}
    runs-on: ubuntu-latest
    steps:
      - run: pre-commit run ${{ matrix.group.hook }} --all-files
```

### Trade-offs

**Pros:**

- Adding a group = adding a JSON entry (no YAML editing)
- Native per-group checks in GitHub UI (may eliminate custom status posting)
- Parallel execution across runners

**Cons:**

- Each matrix job pays separate runner startup + checkout cost
- Summary becomes a separate "collect results" job
- Matrix job outputs not aggregated (need artifact workaround)
- `fromJSON` support in Gitea Actions needs testing
- 256-job limit (not a concern for <20 groups)

### When to Adopt

Consider when:

- Runner startup cost is acceptable (or caching is aggressive enough)
- Gitea `fromJSON` matrix support is confirmed
- The number of linter groups grows beyond ~20

## Linter Evaluation Matrix

Assessment of additional linters for potential inclusion. Status: **already covered**, **added**, **evaluate**, or **skip**.

### Covered

| Tool | Status | How |
|---|---|---|
| shellcheck | Covered | Via `.shellcheckrc` (root-copy config). Used by actionlint for shell in YAML. |
| markdownlint | Covered | `markdownlint-cli2` hook with extends-capable config override. |
| yamllint | Covered | Hook with extends-capable config override. |
| hadolint | Covered | Pre-commit hook + linter group. Full-replacement config override. |
| TFLint | Covered | Binary cached, runs `--recursive`. Gated on `*.tf` file presence. |
| jscpd | Covered | `npx jscpd@4` with npm cache. Full-replacement config override. |
| gitleaks | Covered | Pre-commit hook with extends-capable config override. |
| ruff | Covered | `ruff` + `ruff-format` hooks (Python lint + format). |
| Trivy | Covered | Binary install + `trivy fs` for IaC + dependency vulnerabilities. |
| Semgrep | Covered | `uvx semgrep scan --config auto` for SAST. |
| ~~cspell~~ | Removed | Replaced `typos`, then removed — dictionary grew with tool names/variable names without catching meaningful typos in a shell/YAML-heavy repo. |
| ESLint | Covered | `npx eslint .` (direct, not pre-commit — needs consumer's `node_modules` for plugins). Gated on eslint config file presence. |
| Prettier | Covered | Pre-commit hook with `--check`. Excludes markdown (handled by markdownlint). Gated on `package.json`. |
| tsc --noEmit | Covered | `npx tsc --noEmit`. Gated on `tsconfig.json`. |
| knip | Covered | `npx knip` — zero-config dead code detection for JS/TS. Gated on `package.json`. |
| madge | Covered | `npx madge --circular` — circular dependency detection. Gated on `package.json`. |
| npm audit | Covered | `npm audit --audit-level=high`. Gated on `package-lock.json`. |
| license-checker | Covered | `npx license-checker --production --failOn GPL/AGPL`. Gated on `package-lock.json`. Uses npm package (not Ruby `license_finder`). |

### Not Included (with rationale)

| Tool | Category | Rationale |
|---|---|---|
| **dependency-cruiser** | Architectural boundaries | Requires `.dependency-cruiser.cjs` config — highly project-specific. Best added via `extra-lint-script`. |
| **SonarQube CE** | Holistic review | Requires a running SonarQube server — doesn't fit the "zero-infra" model. |
| **Renovate** | Dependency freshness | Not a linter — separate concern. Consumers configure independently. |
| **secretlint** | Credential scanning | Overlaps with gitleaks. gitleaks has broader pattern coverage and is already integrated. |
| **typos** | Spell checking | Was replaced by cspell, which was then removed — neither provided value in a shell/YAML repo. |
