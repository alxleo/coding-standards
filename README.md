# coding-standards

Drop-in linting image. Add one workflow file — everything else is automatic. Detects your stack, runs the right checks, tells you what to fix.

Native arm64. Works on GitHub Actions and Gitea Actions. Built on MegaLinter.

## Quick start

```bash
# Get the consumer justfile (one-time, no Docker needed)
curl -fsSL https://raw.githubusercontent.com/alxleo/coding-standards/main/consumer.just > consumer.just
echo 'import? "consumer.just"' >> justfile

# Generate CI workflow + .gitignore
just cs-init

# Run locally
just cs-lint
```

That's it. No `.mega-linter.yml` needed — the image auto-detects your stack and runs all applicable checks.

## What happens automatically

The image detects files and activates the right tools:

| Your repo has | Image runs |
|---|---|
| `*.py` | ruff, pyright, vulture, deptry, semgrep |
| `*.js`/`*.ts`/`*.tsx` | eslint, prettier, typescript, knip, oxlint |
| `*.sh` | shellcheck, shfmt |
| `Dockerfile` | hadolint, trivy, dclint |
| `docker-compose.yml` | conftest policies (healthchecks, resource limits, security) |
| `*.tf` | tflint |
| `*.yml`/`*.yaml` | yamllint, prettier, v8r (schema validation) |
| `ansible/` | ansible-lint |
| `*.go` | golangci-lint |
| `package.json` | npm-audit, license-checker, knip, publint |
| `pyproject.toml` | deptry, import-linter |
| `.github/workflows/` | actionlint, zizmor |
| Any code | semgrep (security), gitleaks (secrets), trivy (vulnerabilities), codespell |
| Any repo | repo-standards (setup validation — tells you what's missing) |

## Customize (only when you need to)

```
just cs-help              All commands + available topics
just cs-help setup        First-time CI setup
just cs-help migrate      Get from 200 errors to green CI fast
just cs-help semgrep      Add your own pattern-matching rules
just cs-help conftest     Add your own structural validation policies
just cs-help ruff         Override Python lint config
just cs-help eslint       Override JS/TS lint config
just cs-help suppress     Suppress specific findings
just cs-help disable      Turn off linters that don't apply
just cs-help debug        Troubleshoot a failing linter
```

## Add your own rules

Drop a directory — it runs alongside the baked rules with zero config:

- **`.semgrep/`** — custom semgrep rules (auto-discovered, merged with baked rules)
- **`policy/`** + `conftest.toml` — custom Rego policies (runs alongside baked policies)

## Override config

```yaml
# .mega-linter.yml (only create if you need to customize)
DISABLE_LINTERS:
  - TERRAFORM_TFLINT      # no terraform here
PYTHON_RUFF_CONFIG_FILE: ruff.toml    # use your own ruff config
```

## Docs

- `just cs-help <topic>` — progressive disclosure, per-topic guides
- [Full catalog](docs/catalog.md) — auto-generated inventory of all checks
- [Consumer guide](docs/consumer-guide.md) — detailed setup + customization
- [Config decisions](docs/config-decisions.md) — every decision with rationale
