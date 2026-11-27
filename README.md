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

## Skip build and lint on Markdown-only pull requests

Call [Pull request scope](.github/workflows/pr-scope.yml) from a job in an
existing workflow. Pin `alxleo/coding-standards/.github/workflows/pr-scope.yml`
to a reviewed commit and give the calling job `contents: read`. Add that job
to `needs` for jobs whose validation is independent of Markdown content,
such as a job that lints workflow YAML. Set the optional `runner` input to
reuse an existing Linux runner label.
Set `full-validation-paths` to a single-line JSON array of build inputs
that end in `.md`, such as `'["README.md"]'` for a README declared in
package metadata. Any change to a matching path runs full validation.

```yaml
needs: change-scope
if: ${{ !cancelled() && needs.change-scope.outputs.markdown-only != 'true' }}
```

Keep the original workflow triggers and job names so GitHub still reports
required checks. Skipped jobs satisfy required checks. The reusable workflow
compares the tested merge commit to its first parent. A rename out of a
non-Markdown path still runs validation. Empty diffs, non-PR events, and
classification failures also leave validation enabled. Keep review and other
merge-policy jobs independent of this output. Keep Markdown, text hygiene,
and secret scanning checks active in both lanes. The default `cs-init`
lint job combines these checks with other linters, so leave that job
running on Markdown-only pull requests.

## What runs automatically

| Your repo has | Image runs |
|---|---|
| `*.py` | ruff, pyright, vulture, deptry, semgrep |
| `*.js`/`*.ts`/`*.tsx` | eslint, prettier, typescript, knip, oxlint |
| `*.sh` | shellcheck, shfmt |
| `Dockerfile` | hadolint, dclint |
| `docker-compose.yml` | conftest (healthchecks, resource limits, security) |
| `*.tf` | tflint |
| `*.yml`/`*.yaml` | yamllint, prettier, v8r (schema validation) |
| `ansible/` | ansible-lint |
| `*.go` | golangci-lint |
| `package.json` | npm-audit, license-checker, knip, publint |
| `pyproject.toml` | deptry, import-linter |
| `.github/workflows/` | actionlint, zizmor |
| Repository-wide | Betterleaks (secrets), plus full Semgrep on scheduled and other non-PR runs |
| Any repo | repo-standards (tells you what's missing) |

## Add your own rules

- **`.semgrep/`** adds custom rules to a full Semgrep run in the coding-standards image.
- For a PR check with local Semgrep rules, use the stock per-linter workflow with `semgrep-config`. It checks eligible changed files and reports when it skips the scan.
- **`policy/`** plus `conftest.toml` adds custom structural validation policies.

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
