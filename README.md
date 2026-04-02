# coding-standards

Drop-in Docker image that turns any repo into a well-linted, secure, type-checked codebase. Tells you what to set up, catches bugs, and improves over time.

Built on MegaLinter. Works on GitHub Actions and Gitea Actions.

## Quick Start

```yaml
# .github/workflows/lint.yml
steps:
  - uses: actions/checkout@v4
    with:
      fetch-depth: 0
  - uses: alxleo/coding-standards/docker-action@v1
```

```yaml
# .mega-linter.yml
EXTENDS:
  - https://raw.githubusercontent.com/alxleo/coding-standards/main/.mega-linter-default.yml
```

## What It Does

Three layers of checks — all automatic:

**Enforcement** — linters catch code bugs. Error-tier blocks, warn-tier reports.

**Structural validation** — conftest policies check Docker Compose files for healthchecks, resource limits, restart policies, security issues.

**Repo standards** — checks your repo is set up correctly. Missing pyrightconfig.json? No .gitleaks.toml? Error messages tell you what's missing and how to fix it. [Full catalog →](docs/catalog.md)

## Local Development

```bash
# One-time: extract consumer justfile
docker run --rm ghcr.io/alxleo/coding-standards:latest cat /opt/coding-standards/consumer.just > consumer.just
echo 'import? "consumer.just"' >> justfile

# Then:
just cs-lint              # full suite
just cs-fix               # auto-fix
just cs-help              # all commands + setup guides
just cs-help setup        # first-time CI setup
just cs-help semgrep      # add custom rules
just cs-help migrate      # get to green CI fast
```

## Consumer Override

Override any linter's config with a single line in `.mega-linter.yml`:

```yaml
PYTHON_RUFF_CONFIG_FILE: ruff.toml
REPOSITORY_GITLEAKS_CONFIG_FILE: .gitleaks.toml
```

Suppress semgrep rules without touching the ruleset:

```yaml
REPOSITORY_SEMGREP_ARGUMENTS: >-
  --exclude-rule=trailofbits.python.some-rule
```

Acknowledge repo-standards warnings with documented reasons:

```yaml
# .repo-standards.yml
acknowledged:
  pydantic: "scripts only, no boundary-crossing data"
  pytest_randomly:
    reason: "adding next sprint"
    expires: 2026-04-15
```

## Docs

- [Consumer guide](docs/consumer-guide.md) — setup, customization, contributing
- [Full catalog](docs/catalog.md) — auto-generated inventory of all checks
- [Config decisions](docs/config-decisions.md) — every decision with rationale
