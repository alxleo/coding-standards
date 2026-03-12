# Architecture Decisions & Future Options

## Current Architecture

Data-driven reusable GitHub Actions workflow. Key design:

- `groups.conf` — single source of truth for linter group metadata
- `lint-run.sh` — wraps each lint step, writes `.outcome` files
- `summary.sh` / `report-statuses.sh` — iterate `groups.conf` + `.outcome` files
- `install-tool.sh` — shared script for pinned binary tool installation
- `apply-configs.sh` — config application (used by both `lint.yml` and `action.yml`)
- `lib/common.sh` — shared error extraction helpers

Adding a new linter group: add a step in `lint.yml` + a line in `groups.conf`.

## Evaluated Alternatives

### MegaLinter (oxsecurity/megalinter)

**What:** Comprehensive meta-linter (50+ languages) shipped as a Docker image.

**Pros:**
- Per-linter GitHub commit statuses via GitHubStatusReporter
- `DISABLE` / `DISABLE_LINTERS` for skip lists
- Lower maintenance for adding standard linters

**Cons:**
- No Gitea status reporter (GitHub API only)
- Large Docker image (multi-GB, slow startup)
- `language: system` custom hooks not supported
- Centralized config distribution not built-in
- Dependent on MegaLinter release cycle for linter version updates
- Known issue (#4254) where workspace configs ignored with `LINTER_RULES_PATH`

**Verdict:** Partial fit. Worth revisiting if Gitea compatibility becomes optional or MegaLinter adds a Gitea reporter.

### super-linter

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
