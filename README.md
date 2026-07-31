# coding-standards

Drop-in linting image. One Docker command — detects your stack, runs the right checks, tells you what to fix. Works offline, no accounts, no API calls.

Native amd64 + arm64. Built on MegaLinter.

## Option 1: Just Docker (local, no CI)

```bash
docker run --rm -v .:/tmp/lint ghcr.io/alxleo/coding-standards:latest
```

Results in `megalinter-reports/`. Auto-fix:

```bash
docker run --rm -v .:/tmp/lint ghcr.io/alxleo/coding-standards:latest fix
```

## Option 2: Justfile integration (local + CI)

```bash
curl -fsSL https://raw.githubusercontent.com/alxleo/coding-standards/main/consumer.just > consumer.just
echo 'import? "consumer.just"' >> justfile
just cs-init        # creates CI workflow + .gitignore
just cs-lint        # run locally
just cs-recommend   # what checks to enable for this repo
```

No `.mega-linter.yml` needed — the image auto-detects your stack.

## What runs automatically

| Your repo has | Image runs |
|---|---|
| `*.py` | ruff, pyright, vulture, deptry, semgrep |
| `*.js`/`*.ts`/`*.tsx` | eslint, prettier, typescript, knip, oxlint |
| `*.sh` | shellcheck, shfmt |
| `Dockerfile` | hadolint, trivy, dclint |
| `docker-compose.yml` | conftest (healthchecks, resource limits, security) |
| `*.tf` | tflint |
| `*.yml`/`*.yaml` | yamllint, prettier, v8r (schema validation) |
| `ansible/` | ansible-lint |
| `*.go` | golangci-lint |
| `package.json` | npm-audit, license-checker, knip, publint |
| `pyproject.toml` | deptry, import-linter |
| `.github/workflows/` | actionlint, zizmor |
| Any code | semgrep (security), gitleaks (secrets), trivy (vulnerabilities) |
| Any repo | repo-standards (tells you what's missing) |

## Add your own rules

Drop a directory — runs alongside baked rules, zero config:

- **`.semgrep/`** — custom pattern-matching rules
- **`policy/`** + `conftest.toml` — custom structural validation policies

## Customize

```
just cs-help              All commands + topics
just cs-help semgrep      Add custom rules
just cs-help conftest     Add custom policies
just cs-help ruff         Override Python config
just cs-help suppress     Suppress specific findings
just cs-help migrate      Get from 200 errors to green fast
just cs-help debug        Troubleshoot a failing linter
```

## Docs

- `just cs-help <topic>` — progressive disclosure guides
- `just cs-catalog` — full check inventory (rendered at runtime)
- [Config decisions](docs/config-decisions.md) — every decision with rationale
