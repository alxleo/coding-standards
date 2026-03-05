# coding-standards

**Project class: Shared Infrastructure Package** — a repo consumed by other repos. The product is configuration, tooling, and conventions distributed to a fleet of consumers. See memory for the full pattern catalog.

This repo contains **no repo lists, no secrets, no private information**. It is a pure standards library.

## How it works

Two consumption modes:

1. **Fetch-and-run (preferred):** Consumer repos fetch this repo at runtime via a justfile. No files synced except the justfile itself. See `templates/justfile.consumer`.
2. **File sync (legacy):** A sync workflow in github-standards pushes individual config files to repos via PRs using [BetaHuhn/repo-file-sync-action](https://github.com/BetaHuhn/repo-file-sync-action).

## Key files

- `configs/.pre-commit-config.yaml` — **source of truth** for all pre-commit hooks (single config, used by both this repo and consumers)
- `templates/justfile.consumer` — consumer onboarding template (fetch + symlinks + lint)
- `scripts/compact-run` — LLM-friendly command wrapper, exported to consumers
- `sync-manifest.yml` — declares every managed file with sync metadata
- `scripts/check-manifest-coverage.py` — bidirectional manifest coverage check

## Configs vs Templates

- **Configs** (`configs/`): Baseline configs. Repos may extend them (e.g., add repo-specific gitleaks allowlists) but the baseline should work everywhere.
- **Templates** (`templates/`): Starting points. An LLM agent adapts them per-repo (removes inapplicable sections, adds repo-specific entries).

## Sync boundary

**Everything in `configs/` is synced to consumer repos.** Never add repo-specific hooks, paths, or scripts to files in `configs/` — they will break consumer repos that don't have the same directory structure. Repo-specific checks (like `check-manifest-coverage`) go in CI or the root `justfile` only.

Root symlinks (`.pre-commit-config.yaml` → `configs/.pre-commit-config.yaml`) mean editing the synced file also changes local behavior, and vice versa.

## Sync manifest

`sync-manifest.yml` declares every managed file and its sync behavior (`all`, `opt-in`, `none`). The `check-manifest-coverage` script (run via `just check-manifest` and CI) enforces bidirectional coverage — every file on disk must have a manifest entry and vice versa.

## How consumer config discovery works

Consumer repos use the same `.pre-commit-config.yaml` as this repo. Tools that auto-discover config from the repo root (gitleaks, markdownlint-cli2, commitlint) find their configs via symlinks. Symlinks are declared in `sync-manifest.yml` with `symlink: true` and created by `scripts/apply-symlinks.sh` (called by `just fetch`):

```
.gitleaks.toml -> .coding-standards/configs/.gitleaks.toml
.markdownlint-cli2.yaml -> .coding-standards/configs/.markdownlint-cli2.yaml
commitlint.config.mjs -> .coding-standards/configs/commitlint.config.mjs
scripts/hooks -> .coding-standards/scripts/hooks
```

## Adding a new config

1. Add the file to `configs/` or `templates/`
2. Add an entry to `sync-manifest.yml` with the appropriate sync level
3. If the new config needs root-level discovery, add `symlink: true` to its manifest entry
4. Run `just check-manifest` to verify

## Adding a custom local hook

1. Create `scripts/hooks/{name}` — executable, with comments explaining the rule
2. Add the hook entry to `configs/.pre-commit-config.yaml` with `entry: scripts/hooks/{name}`, `language: system`
3. Add the script to `sync-manifest.yml` under `scripts:`
4. Add a test fixture + assertion to `tests/test-hooks.sh`

The `hooks/` directory symlink (created by `apply-symlinks.sh`) makes `scripts/hooks/{name}` resolve in both this repo and consumer repos.
