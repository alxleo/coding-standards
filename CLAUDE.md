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

## Adding a new config

1. Add the file to `configs/` or `templates/`
2. Update the sync config in github-standards (`.github/sync.yml`) to include the new file
3. Trigger the sync workflow — PRs will be opened in all target repos
