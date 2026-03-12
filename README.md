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
4. Runs pre-commit with all hooks on all files
5. Reports pass/fail

Configs are centralized in this repo. When we update a rule, every consumer gets the update on their next CI run — no PRs, no syncing, no merge conflicts.

## Overrides

### Skip specific hooks

Pass `skip-hooks` input:

```yaml
- uses: alxleo/coding-standards@v1
  with:
    skip-hooks: "commitlint,ruff"
```

### Override via config file

Drop a `.coding-standards.yml` in your repo root:

```yaml
# .coding-standards.yml
skip-hooks:
  - commitlint       # This repo uses a different commit convention
  - ruff             # No Python in this repo
  - ruff-format      # No Python in this repo
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

## What's Included

### Pre-commit Hooks

| Hook | Purpose |
|------|---------|
| check-yaml, check-json, check-toml | Syntax validation |
| check-merge-conflict | Catch unresolved merge markers |
| check-added-large-files | Block files >500KB |
| detect-private-key | Catch committed private keys |
| end-of-file-fixer | Ensure files end with newline |
| trailing-whitespace | Remove trailing whitespace |
| check-case-conflict | Catch case-insensitive filename collisions |
| check-executables-have-shebangs | Ensure executable scripts have shebangs |
| gitleaks | Secret scanning |
| typos | Typo detection |
| actionlint | GitHub Actions workflow linting |
| zizmor | GitHub Actions security linting |
| markdownlint-cli2 | Markdown style |
| commitlint | Conventional commit messages |
| ruff + ruff-format | Python linting and formatting |
| forbid-cruft-files | Block .bak, .del, .tmp, .old, .orig files |
| block-secret-files | Block .env, .key, .pem files |
| verify-sops-encryption | Ensure SOPS files are encrypted |
| pin-npm-versions | Require pinned npx versions |
| temp-file-needs-trap | Shell scripts with mktemp need trap cleanup |
| forbid-bare-python | Require `uv run` instead of bare `python` |
| just-fmt-check | Check justfile formatting |

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
| `skip-hooks` | `''` | Comma-separated pre-commit hook IDs to skip |
| `config-file` | `.coding-standards.yml` | Path to override config in consumer repo |
| `version` | `3.13` | Python version |
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
