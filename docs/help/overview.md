# coding-standards

Centralized linting image. Drop into any repo's CI — it tells you what to set up, catches bugs, and improves over time.

## Getting started

```
just cs-help setup        First-time CI + local setup
just cs-help migrate      Get from 200 errors to green CI
```

## Commands

```
just cs-lint              Full lint suite
just cs-lint-one ruff     Single linter
just cs-fix               Auto-fix all fixable issues
just cs-standards         Repo setup checks
just cs-show-config       Which config each linter uses
just cs-warnings          Warnings from last run
just cs-catalog           Full check inventory
just cs-catalog-rules     Per-tool rule details (--tool, --format json)
just cs-blast-radius      Change impact analysis
just cs-recommend         What checks to enable for this repo (JSON)
just cs-update            Pull latest image
```

## Customize (just cs-help <topic>)

```
setup       First-time setup (CI + local)
migrate     Get to green CI fast
disable     Turn off linters that don't apply
semgrep     Add custom pattern-matching rules
conftest    Add custom structural validation policies
ruff        Override Python lint rules
eslint      Override JS/TS lint rules
override    Override any linter's config
suppress    Suppress specific findings
debug       Troubleshoot a failing linter
local       Running on Mac (native arm64)
gitignore   What to add to .gitignore
rules       Per-tool rule catalog (query any rule by tool/ID)
```
