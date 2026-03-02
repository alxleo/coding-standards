# coding-standards

Shared coding standards, linter configs, and templates for consistent quality across repositories.

## What's here

### Configs (`configs/`)

Baseline configs synced to all repos:

| File | Purpose |
|------|---------|
| `.pre-commit-config.yaml` | Universal pre-commit hooks (YAML/JSON validation, secret scanning, cruft blocking) |
| `.editorconfig` | Consistent formatting (indentation, line endings, charset) |
| `.gitleaks.toml` | Secret scanning configuration |
| `.yamllint` | YAML lint rules (relaxed preset, no line-length limit) |
| `.hadolint.yaml` | Dockerfile lint baseline (trusted registries) |

### Templates (`templates/`)

Starting points adapted per-repo by an LLM agent:

| File | Purpose |
|------|---------|
| `dependabot.yml` | Dependabot config covering GHA, pip, npm, Docker, Terraform ecosystems |

## How syncing works

A separate private repo runs [BetaHuhn/repo-file-sync-action](https://github.com/BetaHuhn/repo-file-sync-action) to push these files to target repos via PRs. This repo has no knowledge of its consumers.

## Using these configs directly

You can also reference these configs manually:

```bash
# Copy a config to your repo
curl -O https://raw.githubusercontent.com/alxleo/coding-standards/main/configs/.pre-commit-config.yaml
```

## Philosophy

- **Baseline, not mandate**: Configs are starting points. Repos can extend them.
- **Language-agnostic core**: The baseline works for any repo. Language-specific tools (shellcheck, ruff, eslint) are added per-repo.
- **LLM-friendly**: Designed for AI-assisted development — strong guardrails that catch common LLM mistakes (secret leaks, cruft files, formatting drift).
