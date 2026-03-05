# coding-standards

Public library of coding standards, linter configs, and templates.

This repo contains **no repo lists, no secrets, no private information**. It is a pure standards library consumed by other repos via file sync.

## How it works

1. Config files live in `configs/` — these are baseline configs synced to all repos
2. Templates live in `templates/` — these are starting points that an LLM agent adapts per-repo
3. A sync workflow in a **separate private repo** (github-standards) pushes these files to target repos via PRs using [BetaHuhn/repo-file-sync-action](https://github.com/BetaHuhn/repo-file-sync-action)

## Configs vs Templates

- **Configs** (`configs/`): Synced as-is. Repos may extend them (e.g., add repo-specific gitleaks allowlists) but the baseline should work everywhere.
- **Templates** (`templates/`): Starting points. An LLM agent adapts them per-repo (removes inapplicable sections, adds repo-specific entries).

## Sync boundary

**Everything in `configs/` is synced to consumer repos.** Never add repo-specific hooks, paths, or scripts to files in `configs/` — they will break consumer repos that don't have the same directory structure. Repo-specific checks (like `check-manifest-coverage`) go in CI or the root `justfile` only.

Root symlinks (`.pre-commit-config.yaml` → `configs/.pre-commit-config.yaml`) mean editing the synced file also changes local behavior, and vice versa.

## Sync manifest

`sync-manifest.yml` declares every managed file and its sync behavior (`all`, `opt-in`, `none`). The `check-manifest-coverage` script (run via `just check-manifest` and CI) enforces bidirectional coverage — every file on disk must have a manifest entry and vice versa.

## Adding a new config

1. Add the file to `configs/` or `templates/`
2. Add an entry to `sync-manifest.yml` with the appropriate sync level
3. Update the sync config in github-standards (`.github/sync.yml`) to include the new file
4. Trigger the sync workflow — PRs will be opened in all target repos
