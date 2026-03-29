# Consumer Guide

## Quick start

```yaml
# .github/workflows/lint.yml (or .gitea/workflows/lint.yml)
name: Lint
on: [push]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - run: docker run --rm -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards:latest
```

That's it. The image auto-detects which linters apply based on files in your repo.

## What runs

41 linters covering: Python, Shell, YAML, JSON, Markdown, Dockerfile, GitHub Actions, Terraform, CSS, SQL, Ansible, Kubernetes, and more. See `docs/config-decisions.md` for the full list.

Two-tier blocking:

- **Errors** (block the build): security tools, type checkers, syntax errors, correctness
- **Warnings** (report but pass): formatters, style, links, schema validation

## Customization

### Override the config

Drop a `.mega-linter.yml` in your repo root. The image auto-detects it (smart entrypoint).

```yaml
# .mega-linter.yml — consumer overrides
DISABLE_LINTERS:
  - TERRAFORM_TFLINT      # no terraform here
  - REPOSITORY_KNIP       # no JS/TS

ANSIBLE_ANSIBLE_LINT_CONFIG_FILE: .ansible-lint
```

### Auto-fix

```bash
docker run --rm -v $PWD:/tmp/lint -e APPLY_FIXES=all ghcr.io/alxleo/coding-standards:latest
```

### Run a single linter

```bash
docker run --rm -v $PWD:/tmp/lint -e ENABLE_LINTERS=PYTHON_RUFF ghcr.io/alxleo/coding-standards:latest
```

### Post commit statuses (Gitea + GitHub)

Add a second CI step:

```yaml
      - name: Post commit statuses
        if: always()
        run: |
          docker run --rm --entrypoint python3 \
            -v $PWD:/tmp/lint \
            -e GITEA_URL=${{ vars.GITEA_URL || '' }} \
            -e GITEA_TOKEN=${{ secrets.GITEA_TOKEN || '' }} \
            -e GITHUB_TOKEN=${{ secrets.GITHUB_TOKEN }} \
            -e GITHUB_REPOSITORY=${{ github.repository }} \
            -e GITHUB_SHA=${{ github.sha }} \
            -e GITHUB_RUN_ID=${{ github.run_id }} \
            -e GITHUB_SERVER_URL=${{ github.server_url }} \
            ghcr.io/alxleo/coding-standards:latest \
            /opt/coding-standards/scripts/report-statuses.py \
            megalinter-reports/mega-linter-report.json
```

Or add as an opt-in POST_COMMAND in your `.mega-linter.yml`:

```yaml
POST_COMMANDS:
  - command: >-
      python3 /opt/coding-standards/scripts/report-statuses.py
      megalinter-reports/mega-linter-report.json
    cwd: workspace
    secured_env: false
    continue_if_failed: true
```

## Adding custom checks

Five mechanisms are available — use the one that fits your check category.

### 1. Semgrep rules (pattern matching)

Add a `.semgrep/` directory with YAML rules. MegaLinter auto-discovers them.

```yaml
# .semgrep/my-rules.yml
rules:
  - id: no-latest-tag
    pattern: "image: $IMG"
    message: Pin image versions
    languages: [yaml]
    severity: ERROR
```

### 2. Conftest policies (structural validation)

Create `conftest.toml` + `policy/` directory with Rego policies.

```rego
# policy/compose/resources.rego
package compose.resources
import rego.v1
deny contains msg if {
    some name, svc in input.services
    not svc.deploy.resources.limits.memory
    msg := sprintf("service '%s' missing memory limit", [name])
}
```

### 3. Generated file drift

Use the baked-in drift checker via POST_COMMANDS:

```yaml
POST_COMMANDS:
  - command: /opt/coding-standards/scripts/check-drift.sh "python3 scripts/generate-catalog.py" catalog.json
    cwd: workspace
    continue_if_failed: false
```

### 4. Expiry enforcement

```yaml
POST_COMMANDS:
  - command: python3 /opt/coding-standards/scripts/check-expiry.py .
    cwd: workspace
    continue_if_failed: false
```

### 5. Per-linter config overrides

Override any linter's config by setting `<LINTER>_CONFIG_FILE` in your `.mega-linter.yml`:

```yaml
YAML_YAMLLINT_CONFIG_FILE: .yamllint
PYTHON_RUFF_CONFIG_FILE: ruff.toml
```

## Migrating to new rules

When coding-standards adds new ruff rules, your repo may get hundreds of new findings. Use this one-command migration:

```bash
# Auto-fix what's fixable, suppress the rest with inline comments
uvx ruff check --config lint-configs-626465/ruff.toml --fix . && \
uvx ruff check --config lint-configs-626465/ruff.toml --add-noqa .
```

This gets your CI green immediately. Clean up the `# noqa` suppressions over time — each one is a TODO, not permanent tech debt.

For shellcheck findings (e.g., `require-double-brackets`):
```bash
# No auto-fix — manually replace [ ] with [[ ]] in bash scripts
# Focus on scripts you actively maintain first
```

## Local development (Mac)

The image is amd64. On Apple Silicon it runs under Rosetta (slower but works):

```bash
docker run --rm --platform linux/amd64 -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards:latest
```

For faster local linting, use the tools directly:

```bash
uvx ruff check .
uvx semgrep scan --config auto .
shellcheck scripts/*.sh
```

## Rollback

If the image breaks, revert to upstream MegaLinter directly:

```yaml
      - run: |
          docker run --rm -v $PWD:/tmp/lint \
            -e ENABLE_LINTERS=BASH_SHELLCHECK,PYTHON_RUFF,YAML_YAMLLINT \
            oxsecurity/megalinter-cupcake:v9
```

Add your own `.mega-linter.yml` for configuration when using upstream directly.

## Reading results

The JSON report at `megalinter-reports/mega-linter-report.json` has structured per-linter data. Quick summary:

```bash
python3 -c "
import json
r = json.load(open('megalinter-reports/mega-linter-report.json'))
for l in r['linters']:
    s = '✅' if l['return_code'] == 0 else '❌'
    print(f'{s} {l[\"name\"]:40s} {l.get(\"total_number_errors\",0)} errors')
"
```
