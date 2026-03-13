# coding-standards

**Project class: Reusable Workflow** — a reusable GitHub Actions workflow consumed by other repos via `uses: alxleo/coding-standards/.github/workflows/lint.yml@v1`. The product is centralized linting + security scanning that runs in CI, not on developer machines.

This repo contains **no repo lists, no secrets, no private information**. It is a public linting workflow.

## How it works

Consumer repos add a short workflow stub. The reusable workflow:

1. Checks out the consumer repo + this repo's configs (sparse checkout)
2. Installs Python, Node.js, pre-commit (all cached)
3. Self-selects tool installs (just, OpenTofu, TFLint) based on file presence
4. Copies linter configs into the workspace (skips files that already exist)
5. Runs each linter group as a separate visible step
6. Runs security scanning (Trivy + Semgrep)
7. Posts per-group commit statuses via the Commit Status API (GitHub + Gitea)
8. Writes a step summary (GitHub only — Gitea does not render `$GITHUB_STEP_SUMMARY`)
9. Prints a summary table and fails the job if any group failed

## Key files

- `.github/workflows/lint.yml` — reusable workflow (main entry point for consumers)
- `.github/workflows/ci.yml` — self-test that calls lint.yml on this repo
- `action.yml` — composite action (calls `apply-configs.sh`, used internally)
- `lint-configs-626465/` — all linter configs (referenced via `--config` paths at runtime)
- `lint-configs-626465/.pre-commit-config.yaml` — source of truth for all pre-commit hooks
- `scripts/ci/groups.conf` — single source of truth for linter group metadata
- `scripts/ci/lint-run.sh` — lint step wrapper (logs, outcomes, error annotations)
- `scripts/ci/summary.sh` — summary table + GitHub step summary
- `scripts/ci/report-statuses.sh` — per-group commit status posting
- `scripts/ci/install-tool.sh` — data-driven binary tool installer
- `scripts/ci/apply-configs.sh` — config application + consumer override merging
- `scripts/ci/lib/common.sh` — shared error extraction helpers
- `scripts/hooks/` — custom hook scripts referenced by pre-commit config
- `test/*.bats` — bats-core tests for CI scripts and hooks
- `docs/architecture-decisions.md` — evaluated alternatives + future options
- `examples/lint.yml` — example consumer workflow
- `examples/.coding-standards.yml` — example override file

## Commit status reporting

Each linter group posts its own commit status (e.g. `coding-standards: python`) via `POST /repos/{owner}/{repo}/statuses/{sha}`. This API is supported by both GitHub and Gitea.

- Statuses are posted for all groups that ran (success or failure)
- Skipped groups do not post a status
- Each status includes a `target_url` linking to the workflow run
- Requires `statuses: write` permission in the caller workflow

LLM agents can query `GET /repos/{owner}/{repo}/commits/{sha}/statuses` and filter by `coding-standards:` prefix to programmatically check results.

## Override mechanism

Consumer repos can:

1. **Skip groups** — via `skip-hooks` workflow input or `.coding-standards.yml` in repo root
2. **Extend linter configs** — for tools with native extends support (yamllint, gitleaks, markdownlint, commitlint), specify an override file in `.coding-standards.yml` that extends the baseline. The consumer's file chains to our `.baseline` config via the tool's native inheritance.
3. **Replace linter configs** — for tools without extends (hadolint, jscpd, prettier, shellcheck, editorconfig), drop the config at repo root for full replacement.

The `.pre-commit-config.yaml` always comes from this repo (it defines which hooks run).

## Adding a new config

1. Add the file to `lint-configs-626465/`
2. Add it to the `configs` array in `.github/workflows/lint.yml` (the "Apply coding-standards configs" step)
3. Update the README tables

## Adding a custom hook

1. Create `scripts/hooks/{name}` — executable, with comments explaining the rule
2. Add the hook entry to `lint-configs-626465/.pre-commit-config.yaml` with `entry: scripts/hooks/{name}`, `language: system`

## Adding a new linter group

1. Add a new step in `.github/workflows/lint.yml` with a unique `id`, `continue-on-error: true`, and the `!contains(env.SKIP_HOOKS, 'group-name')` guard, wrapping the command with `/tmp/lint-run.sh <logkey> <command>`
2. Add a line in `scripts/ci/groups.conf` with `logkey|display_name|status_context|step_name`
3. Update the README linter groups table
4. Update `examples/.coding-standards.yml` available groups comment

That's it — `report-statuses.sh` and `summary.sh` are data-driven from `groups.conf`.

## Running tests

```bash
just test     # bats-core tests (58 tests across CI scripts + hooks)
just lint     # full lint suite (mirrors CI)
```

## CI self-test

`.github/workflows/ci.yml` calls `./.github/workflows/lint.yml` (local ref) to test the workflow against this repo. If CI passes, the workflow works.

## Gitea compatibility

The workflow targets both GitHub Actions and Gitea Actions. Key differences:

- **Commit Status API**: Works identically on both platforms
- **`$GITHUB_STEP_SUMMARY`**: Not rendered in Gitea (harmless no-op — file is written, just not displayed)
- **Third-party actions** (trivy-action, cache, setup-node): Gitea runners must be able to resolve GitHub-hosted action references
