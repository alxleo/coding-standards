# coding-standards

Shared coding standards, linter configs, and templates synced across repositories. Provides a universal baseline that repos extend with language-specific tooling.

## Quick Start

For repos receiving these configs via sync:

```bash
# 1. Check prerequisites
just doctor

# 2. Install git hooks (idempotent — safe to re-run)
just setup

# 3. Run all linters manually
just lint
```

After sync, customize per-repo:

- **`.pre-commit-config.yaml`** — Add language-specific hooks (eslint, shellcheck, hadolint, mypy)
- **`.gitleaks.toml`** — Add `allowlist` entries for known false positives
- **`.hadolint.yaml`** — Add `ignore` rules with documented reasoning
- **Templates** in `templates/` — An LLM agent adapts these per-repo (removes inapplicable sections, adds repo-specific entries)

## Architecture

```
coding-standards/
├── configs/                 ← Synced as-is to all repos
│   ├── .pre-commit-config.yaml   Core hooks (hygiene, secrets, formatting)
│   ├── .editorconfig             Indentation, line endings, charset
│   ├── .gitleaks.toml            Secret scanning rules
│   ├── .yamllint                 YAML lint (relaxed, no line-length)
│   ├── .hadolint.yaml            Dockerfile lint
│   ├── .shellcheckrc             ShellCheck rules
│   ├── .markdownlint-cli2.yaml   Markdown lint
│   ├── .prettierrc               Prettier formatting
│   ├── .jscpd.json               Copy-paste detection (informational)
│   ├── .mega-linter.yml          MegaLinter baseline
│   ├── .envrc.snippet            Direnv auto-install hooks
│   ├── commitlint.config.mjs     Conventional commit rules
│   └── justfile                   Task runner (setup, doctor, lint, clean)
│
├── templates/               ← Starting points, adapted per-repo by LLM
│   ├── dependabot.yml            Dependabot multi-ecosystem config
│   ├── eslint.config.baseline.mjs ESLint flat config (Node.js)
│   ├── pyproject.toml.baseline   Ruff config (Python)
│   └── pull_request_template.md  PR template (What/Why/Test)
│
├── workflows/               ← CI templates synced to consumer repos
│   ├── lint-baseline.yml         Thin caller → reusable lint workflow
│   └── security-scan.yml         Trivy + Semgrep scanning
│
├── scripts/                 ← Local git hook wrappers + utilities
│   ├── setup-hooks.sh            Installs pre-commit + 4 custom hooks
│   ├── compact-run               LLM-friendly output wrapper
│   ├── git-pre-commit.sh         Lint staged files (quiet on success)
│   ├── git-commit-msg.sh         Validate conventional commits
│   ├── git-post-commit.sh        Auto-clean cruft files
│   └── git-pre-push.sh           Block push to main + full validation
│
├── tests/                   ← Test suite for hook validation
│   ├── test-hooks.sh             Negative tests (each hook catches its fixture)
│   ├── test-git-hooks.bats       Integration tests for hook wrappers
│   ├── test-compact-run.bats     Unit tests for compact-run
│   └── fixtures/                 Intentionally-bad files for negative tests
│
├── sync-manifest.yml        ← Declares every file and its sync behavior
│
└── .github/workflows/       ← CI for THIS repo (not synced)
    ├── lint.yml                  Reusable lint workflow (called by consumers)
    └── ci.yml                    Self-test CI
```

### What's synced vs local-only

| Synced to consumer repos | Local to this repo |
|--------------------------|-------------------|
| `configs/*` (incl. justfile) | `scripts/*` |
| `templates/*` | `tests/*` |
| `workflows/*` | root `justfile` (imports configs/justfile + dev tasks) |
| | `.github/workflows/*` |

Sync is handled by a separate private repo ([github-standards](https://github.com/BetaHuhn/repo-file-sync-action)) that opens PRs in target repos. This repo has no knowledge of its consumers.

## Configs Reference

### Hygiene

| File | Purpose | Extend after sync? |
|------|---------|-------------------|
| `.pre-commit-config.yaml` | Universal pre-commit hooks: YAML/JSON/TOML validation, secret scanning, typo detection, GHA linting, markdown, commitlint, Python formatting | Yes — add language-specific hooks |
| `.editorconfig` | Consistent indentation, line endings, charset | No |
| `.yamllint` | YAML lint rules (relaxed comments, no line-length) | No |
| `.shellcheckrc` | ShellCheck rules (check-extra-masked-returns, external-sources) | Yes — add rule disables |

### Security

| File | Purpose | Extend after sync? |
|------|---------|-------------------|
| `.gitleaks.toml` | Secret scanning baseline | Yes — add allowlists for false positives |
| `.hadolint.yaml` | Dockerfile lint (trusted registries, strict labels) | Yes — add rule ignores with reasoning |

### Formatting

| File | Purpose | Extend after sync? |
|------|---------|-------------------|
| `.prettierrc` | Prettier config (semicolons, double quotes, 100 width) | No |
| `.markdownlint-cli2.yaml` | Markdown lint (disabled: line-length, inline HTML) | No |
| `commitlint.config.mjs` | Conventional commit rules | No |

### CI / Quality

| File | Purpose | Extend after sync? |
|------|---------|-------------------|
| `.jscpd.json` | Copy-paste detection (threshold: 5, informational only) | No |
| `.mega-linter.yml` | MegaLinter baseline | Optional |

### Developer Experience

| File | Purpose | Extend after sync? |
|------|---------|-------------------|
| `.envrc.snippet` | Source in `.envrc` to auto-install hooks on `cd` | Yes — merge into existing `.envrc` |

## Templates Reference

Templates are starting points. An LLM agent adapts them per-repo after sync.

| File | Purpose | What gets adapted |
|------|---------|-------------------|
| `dependabot.yml` | Multi-ecosystem Dependabot | Remove unused ecosystems; add per-directory entries for monorepos |
| `eslint.config.baseline.mjs` | ESLint flat config (Node.js) | Add/remove plugins, parser configs, test file exceptions |
| `pyproject.toml.baseline` | Ruff config (Python) | Adjust line-length, target version, add per-repo rules |
| `pull_request_template.md` | PR template (What/Why/Architecture/Test) | Customize sections, add repo-specific runbook links |

## Workflow Templates

### `lint-baseline.yml`

Thin caller synced to consumer repos. Invokes the reusable lint workflow hosted in this repo:

```yaml
uses: alxleo/coding-standards/.github/workflows/lint.yml@main
```

The reusable workflow auto-detects which tools to install based on file presence (`hashFiles`): just, OpenTofu, TFLint, Node.js. All tool installs use checksum-verified downloads.

### `security-scan.yml`

Standalone workflow running Trivy (IaC + dependency scanning) and Semgrep (SAST). Synced to consumer repos, runs on PR and push to main.

## Git Hooks

`just setup` (or `bash scripts/setup-hooks.sh`) installs four custom git hooks:

| Hook | Trigger | Behavior |
|------|---------|----------|
| **pre-commit** | `git commit` | Lints staged files via pre-commit. Quiet on success, full output on failure. |
| **commit-msg** | `git commit` | Validates conventional commit format via commitlint. |
| **post-commit** | After commit succeeds | Auto-removes untracked cruft files (`.bak`, `.del`, `.tmp`, `.old`, `.orig`) and empty directories. Skips tracked files. |
| **pre-push** | `git push` | Blocks direct push to `main`. Runs full `pre-commit --all-files` validation. |

### compact-run

All hooks use `compact-run` for LLM-friendly output:

```
Success:  ✓ 12 lines (0.8s)
Failure:  ✗ exit 1 — 247 lines (2.3s)
          [first 15 lines of output]
          ... 232 more lines → /tmp/compact-run-a3f2.log
```

Full logs always saved to `/tmp/compact-run-*.log`. Configurable via:

- `COMPACT_LINES=15` — Error lines shown inline (default: 15)
- `COMPACT_THRESHOLD=30` — Below this, show full output on failure (default: 30)

### Auto-install via direnv

Add to your `.envrc`:

```bash
source_url "https://raw.githubusercontent.com/alxleo/coding-standards/main/configs/.envrc.snippet" \
  "sha256-XXXX"
```

Hooks install automatically on first `cd` into the repo if not already present.

## Development

### Prerequisites

| Tool | Required? | Purpose |
|------|-----------|---------|
| [just](https://just.systems) | Yes | Task runner |
| [uv](https://docs.astral.sh/uv/) | Yes | Python tool management (runs pre-commit) |
| [bats](https://bats-core.readthedocs.io/) | For testing | Bash test framework |
| git | Yes | Version control |

Run `just doctor` to check what's installed.

### Tasks

Consumer tasks (in `configs/justfile`, synced to repos):

```bash
just setup          # Install hooks
just doctor         # Check prerequisites
just lint           # Run pre-commit on all files
just clean          # Remove cruft files
```

Dev tasks (in root `justfile`, local only):

```bash
just test           # Run all tests
just test-hooks     # Run negative tests (each hook catches its fixture)
just test-git-hooks # Run integration tests (hook wrappers in sandbox repos)
```

### Adding a new config

1. Add the file to `configs/`
2. Add an entry to `sync-manifest.yml` (`sync: all` or `sync: opt-in`)
3. Update the sync config in github-standards (`.github/sync.yml`)
4. Add a row to the Configs Reference table in this README
5. If the config needs a negative test fixture, add one to `tests/fixtures/` and a test case to `tests/test-hooks.sh`

### Adding a new template

1. Add the file to `templates/` with a `.baseline` suffix if it will be renamed per-repo
2. Add an entry to `sync-manifest.yml`
3. Add a row to the Templates Reference table
4. Document what an LLM agent should adapt

### Test strategy

- **Negative tests** (`test-hooks.sh`): Each pre-commit hook has an intentionally-bad fixture file. Tests verify the hook catches the violation. Fixtures are excluded from normal lint runs via `exclude: ^tests/fixtures/`.
- **Integration tests** (`test-git-hooks.bats`): Create throwaway git repos, install hooks, verify behavior (quiet on success, loud on failure, cruft cleanup, push blocking).
- **Unit tests** (`test-compact-run.bats`): Verify compact-run output formatting, threshold behavior, and edge cases.

## Philosophy

- **Baseline, not mandate** — Configs are starting points. Repos extend them with language-specific tooling.
- **Language-agnostic core** — The baseline works for any repo. Language-specific tools (shellcheck, ruff, eslint) are added per-repo.
- **LLM-friendly** — Strong guardrails that catch common AI-generated mistakes: secret leaks, cruft files, formatting drift, unpinned dependencies.
- **Quiet on success** — Hooks and CI produce minimal output when everything passes. Full diagnostics only on failure, with logs saved to `/tmp/`.
