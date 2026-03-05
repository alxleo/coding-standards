# coding-standards

**Project class: Shared Infrastructure Package** — a repo consumed by other repos. The product is configuration, tooling, and conventions distributed to a fleet of consumers. See memory for the full pattern catalog.

This repo contains **no repo lists, no secrets, no private information**. It is a pure standards library.

## How it works

Two consumption modes:

1. **Fetch-and-run (preferred):** Consumer repos fetch this repo at runtime via a justfile. No files synced except the justfile itself. See `templates/justfile.consumer`.
2. **File sync (legacy):** A sync workflow in github-standards pushes individual config files to repos via PRs using [BetaHuhn/repo-file-sync-action](https://github.com/BetaHuhn/repo-file-sync-action).

## Key files

- `configs/.pre-commit-config.yaml` — **source of truth** for all pre-commit hooks
- `configs/.pre-commit-config.remote.yaml` — **generated** (don't edit). Consumer version with `--config` args. Regenerate: `just generate-remote-config`
- `templates/justfile.consumer` — consumer onboarding template
- `sync-manifest.yml` — declares every managed file with sync metadata
- `scripts/generate-remote-config.py` — generates remote config from baseline
- `scripts/check-manifest-coverage.py` — bidirectional manifest coverage check

## Configs vs Templates

- **Configs** (`configs/`): Baseline configs. Repos may extend them (e.g., add repo-specific gitleaks allowlists) but the baseline should work everywhere.
- **Templates** (`templates/`): Starting points. An LLM agent adapts them per-repo (removes inapplicable sections, adds repo-specific entries).

## Sync boundary

**Everything in `configs/` is synced to consumer repos.** Never add repo-specific hooks, paths, or scripts to files in `configs/` — they will break consumer repos that don't have the same directory structure. Repo-specific checks (like `check-manifest-coverage`) go in CI or the root `justfile` only.

Root symlinks (`.pre-commit-config.yaml` → `configs/.pre-commit-config.yaml`) mean editing the synced file also changes local behavior, and vice versa.

## Sync manifest

`sync-manifest.yml` declares every managed file and its sync behavior (`all`, `opt-in`, `none`). The `check-manifest-coverage` script (run via `just check-manifest` and CI) enforces bidirectional coverage — every file on disk must have a manifest entry and vice versa.

## Generated files — do not edit directly

| Generated file | Source | Regenerate |
|---------------|--------|------------|
| `configs/.pre-commit-config.remote.yaml` | `configs/.pre-commit-config.yaml` | `just generate-remote-config` |

CI runs drift checks for both the manifest and the remote config. If you edit the baseline pre-commit config, regenerate the remote version.

## Adding a new config

1. Add the file to `configs/` or `templates/`
2. Add an entry to `sync-manifest.yml` with the appropriate sync level
3. If the new config is used by a pre-commit hook, add a `--config` entry to `CONFIG_OVERRIDES` in `scripts/generate-remote-config.py` and regenerate
4. Run `just check-manifest` and `just check-remote-config` to verify
