# coding-standards

Centralized linting and coding standards as a GitHub Action. Consumer repos add a ~6-line workflow — all linting runs in CI, not on developer machines.

Works with both **GitHub Actions** and **Gitea Actions** (same `uses:` reference).

## Quick Start

Add this workflow to your repo at `.github/workflows/lint.yml`:

```yaml
name: Lint

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  push:
    branches: [main]

jobs:
  lint:
    if: github.event.pull_request.draft == false
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: alxleo/coding-standards@v1
```

That's it. All linting configs are baked into the action.

## How It Works

The action:

1. Checks out your code (you do this)
2. Installs Python, Node.js, and pre-commit (cached)
3. Copies baseline linter configs into the workspace (won't overwrite your own)
4. Runs each linter group as a **separate step** — failures are isolated
5. Prints a summary table showing pass/fail/skip per group

Each linter group gets its own collapsible step in the GitHub Actions UI. If markdown linting fails, you click "Lint: markdown" and see exactly what's wrong — no digging through a wall of mixed output.

Configs are centralized in this repo. When we update a rule, every consumer gets the update on their next CI run — no PRs, no syncing, no merge conflicts.

## Overrides

### Skip linter groups

Pass `skip-hooks` input with group names:

```yaml
- uses: alxleo/coding-standards@v1
  with:
    skip-hooks: "commitlint,python"
```

Available groups: `hygiene`, `cruft`, `gitleaks`, `typos`, `actions`, `markdown`, `commitlint`, `python`, `shell`, `justfile`

### Override via config file

Drop a `.coding-standards.yml` in your repo root:

```yaml
# .coding-standards.yml
skip-hooks:
  - commitlint       # This repo uses a different commit convention
  - python           # No Python in this repo
  - justfile         # No justfiles in this repo
```

Either everything passes or the skip is **explicit in the repo**. No hidden ignores.

### Override individual linter configs

The action only copies config files that don't already exist in your repo. To override a specific linter's config, just add your own file:

- `.yamllint` — Custom YAML lint rules
- `.shellcheckrc` — Custom ShellCheck rules
- `.gitleaks.toml` — Custom secret scanning allowlists
- `.hadolint.yaml` — Custom Dockerfile lint rules
- `.prettierrc` — Custom Prettier config
- `.markdownlint-cli2.yaml` — Custom Markdown lint rules

The action's `.pre-commit-config.yaml` always takes precedence (it defines which hooks run).

## Linter Groups

Each group runs as a separate CI step with isolated output:

| Group | Hooks | What it checks |
|-------|-------|----------------|
| `hygiene` | check-yaml, check-json, check-toml, check-merge-conflict, check-added-large-files, detect-private-key, end-of-file-fixer, trailing-whitespace, check-case-conflict, check-executables-have-shebangs | Basic file hygiene |
| `cruft` | forbid-cruft-files, block-secret-files, verify-sops-encryption | Cruft and secret file blocking |
| `gitleaks` | gitleaks | Secret scanning in file contents |
| `typos` | typos | Typo detection |
| `actions` | actionlint, zizmor | GitHub Actions workflow linting + security |
| `markdown` | markdownlint-cli2 | Markdown style |
| `commitlint` | commitlint | Conventional commit messages |
| `python` | ruff, ruff-format | Python linting and formatting |
| `shell` | pin-npm-versions, temp-file-needs-trap, forbid-bare-python | Shell script hygiene |
| `justfile` | just-fmt-check | Justfile formatting |

### Baked-in Configs

| Config | Key settings |
|--------|-------------|
| `.yamllint` | No line-length limit, relaxed comments, no document-start, truthy keys allowed |
| `.shellcheckrc` | check-extra-masked-returns, deprecate-which, external-sources |
| `.gitleaks.toml` | Default ruleset |
| `.hadolint.yaml` | Trusted registries (docker.io, ghcr.io), strict labels, warning threshold |
| `.markdownlint-cli2.yaml` | No line-length, no inline-HTML restriction, duplicate headings in different sections OK |
| `.prettierrc` | Semicolons, double quotes, 2-space indent, trailing commas, 100 width |
| `.editorconfig` | LF line endings, UTF-8, language-specific indent sizes |
| `.jscpd.json` | Copy-paste threshold: 5 clones, 10+ lines, 50+ tokens |
| `commitlint.config.mjs` | @commitlint/config-conventional |

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `skip-hooks` | `''` | Comma-separated linter groups to skip |
| `config-file` | `.coding-standards.yml` | Path to override config in consumer repo |
| `python-version` | `3.13` | Python version |
| `node-version` | `22` | Node.js version |

## Version Pinning

Pin to a major version tag:

```yaml
- uses: alxleo/coding-standards@v1
```

The `v1` tag moves forward with non-breaking updates. Pin to a specific release (`@v1.0.3`) if you need exact reproducibility.

## Philosophy

- **CI-only enforcement** — No local tooling burden. Developers write code, CI enforces standards.
- **Non-blocking** — Failures are visible but don't prevent commits or pushes locally.
- **Explicit overrides** — If a repo skips a check, it's visible in the repo's `.coding-standards.yml`.
- **One artifact** — This repo is the single source of truth. Update once, all consumers get it.
- **Cross-platform** — Works on GitHub Actions and Gitea Actions with the same `uses:` reference.
