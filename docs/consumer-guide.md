# Consumer Guide

## Quick start

### CI workflow (Gitea + GitHub Actions)

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
      - uses: alxleo/coding-standards/docker-action@v1
```

### Inherit the baseline config

Add a `.mega-linter.yml` to your repo root:

```yaml
EXTENDS:
  # Tracks main for automatic updates. Pin to a tag (e.g. /v1/) for strict reproducibility.
  - https://raw.githubusercontent.com/alxleo/coding-standards/main/.mega-linter-default.yml

# Override what you need — your keys win over the baseline
ENABLE_LINTERS:
  - BASH_SHELLCHECK
  - PYTHON_RUFF
  - YAML_YAMLLINT
  # ... add what your repo needs

# Use your repo's own linter config
PYTHON_RUFF_CONFIG_FILE: ruff.toml
```

Without a `.mega-linter.yml`, the image runs with its baked defaults (all 41 linters, baseline configs).

The image auto-detects which linters apply based on files in your repo.

## What runs

41 linters covering: Python, Shell, YAML, JSON, Markdown, Dockerfile, GitHub Actions, Terraform, CSS, SQL, Ansible, Kubernetes, and more. See `docs/config-decisions.md` for the full list.

Two-tier blocking:

- **Errors** (block the build): security tools, type checkers, syntax errors, correctness
- **Warnings** (report but pass): formatters, style, links, schema validation

## Customization

### Override the config

Drop a `.mega-linter.yml` in your repo root. MegaLinter natively discovers it.

```yaml
# .mega-linter.yml — consumer overrides
DISABLE_LINTERS:
  - TERRAFORM_TFLINT      # no terraform here
  - REPOSITORY_KNIP       # no JS/TS

# Use your repo's own linter config — just set _CONFIG_FILE.
# MegaLinter passes it via the appropriate mechanism (CLI flag or native discovery).
ANSIBLE_ANSIBLE_LINT_CONFIG_FILE: .ansible-lint
PYTHON_RUFF_CONFIG_FILE: ruff.toml
REPOSITORY_GITLEAKS_CONFIG_FILE: .gitleaks.toml
```

### Suppress specific semgrep rules

The baseline ships `auto` + `p/trailofbits` + custom rules. To suppress specific rules without touching the rulesets array (which breaks due to EXTENDS array merge):

```yaml
# .mega-linter.yml — suppress individual semgrep rules
REPOSITORY_SEMGREP_ARGUMENTS: >-
  --exclude-rule=trailofbits.python.some-noisy-rule
  --exclude-rule=generic.secrets.false-positive
```

Or inline in code: `# nosemgrep: rule-id`

Do NOT override `REPOSITORY_SEMGREP_RULESETS` — it contains absolute image paths that break when merged with consumer values.

### Built-in commands

The image has a command router — no setup needed:

```bash
docker run --rm -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards:latest              # full lint
docker run --rm -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards:latest lint PYTHON_RUFF     # single linter
docker run --rm -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards:latest fix           # auto-fix all
docker run --rm -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards:latest standards     # repo-standards only
docker run --rm -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards:latest catalog       # show what's checked
docker run --rm -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards:latest help          # list commands
```

For shorter commands, copy `examples/justfile` into your repo root:

```bash
just cs-lint PYTHON_RUFF      # same as the docker run above
just cs-fix            # auto-fix
just cs-standards      # repo-standards
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
            /opt/coding-standards/scripts/megalinter_report_statuses.py \
            megalinter-reports/mega-linter-report.json
```

Or add as an opt-in POST_COMMAND in your `.mega-linter.yml`:

```yaml
POST_COMMANDS:
  - command: >-
      python3 /opt/coding-standards/scripts/megalinter_report_statuses.py
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
  - command: /opt/coding-standards/scripts/check-drift.sh "python3 scripts/generate_catalog.py" catalog.json
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
uvx ruff check --config lint-configs/ruff.toml --fix . && \
uvx ruff check --config lint-configs/ruff.toml --add-noqa .
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

## Repo standards (setup validation)

The image checks whether your repo is set up to benefit from the enforcement layer. These are warnings, not blockers — they tell you what's missing and how to fix it.

Checks auto-detect your stack: Python-only repos won't get JS/TS warnings.

See `docs/catalog.md` for the full list of checks (generated, always current).

### Acknowledge warnings

If a check doesn't apply, silence it with a reason in `.repo-standards.yml`:

```yaml
# .repo-standards.yml
acknowledged:
  # Permanent: string reason — check doesn't apply to this repo
  commitlint_config: "uses baked commitlint from coding-standards image"
  pydantic: "scripts only, no boundary-crossing data"

  # Temporary: will fix later — MUST have expires date
  pytest_randomly:
    reason: "adding next sprint"
    expires: 2026-04-15
    tracking: "#123"

  # Per-file: list of {path, reason} excludes specific files from counts
  large_shell_scripts:
    - path: scripts/backup-docker-volumes.sh
      reason: "orchestrates 5 backup targets sequentially"
```

**String = permanent** ("not applicable"). **Object with `expires` = temporary** ("will fix"). Expired temporaries are automatically stripped — the warning reappears when the date passes.

The acknowledgment IS the documentation — versioned, reviewable, lives next to the code.

### Promote to blocking

Add a `.rego` file in your `policy/repo-standards/` that uses `deny` instead of `warn`:

```rego
package repo_standards.local

import data.repo_standards.python

deny := python.warn
```

## Full catalog

See `docs/catalog.md` — auto-generated inventory of all linters, semgrep rules, conftest policies, and repo-standards checks. Run `python3 scripts/generate_catalog.py` to regenerate.

## Contributing new checks

Adding a check to the coding-standards image:

1. **Decide where it lives:**
   - File/config presence → repo-standards Rego policy + manifest field
   - Code pattern → semgrep rule
   - Config content → conftest compose policy
   - Code quality → ruff rule category

2. **For repo-standards checks:**
   - Add manifest field in `scripts/generate_repo_manifest.py`
   - Add `warn contains msg` rule in `policies/repo-standards/<category>.rego`
   - Add unit test in `policies/repo-standards/<category>_test.rego`
   - Run `conftest verify -p policies/repo-standards/`

3. **For semgrep rules:**
   - Add rule to existing or new file in `semgrep-rules/`
   - Run `semgrep scan --config semgrep-rules/<file>.yml --validate`

4. **Regenerate catalog:** `python3 scripts/generate_catalog.py`

5. **Test against a real repo:** `python3 scripts/generate_repo_manifest.py ~/path/to/repo`
