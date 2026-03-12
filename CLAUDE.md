# coding-standards

**Project class: Reusable Workflow** — a reusable GitHub Actions workflow consumed by other repos via `uses: alxleo/coding-standards/.github/workflows/lint.yml@v1`. The product is centralized linting + security scanning that runs in CI, not on developer machines.

This repo contains **no repo lists, no secrets, no private information**. It is a public linting workflow.

## How it works

Consumer repos add a ~5-line workflow stub. The reusable workflow:

1. Checks out the consumer repo + this repo's configs (sparse checkout)
2. Installs Python, Node.js, pre-commit (all cached)
3. Self-selects tool installs (just, OpenTofu, TFLint) based on file presence
4. Copies linter configs into the workspace (skips files that already exist)
5. Runs each linter group as a separate visible step
6. Runs security scanning (Trivy + Semgrep)
7. Prints a summary table

## Key files

- `.github/workflows/lint.yml` — reusable workflow (main entry point for consumers)
- `.github/workflows/ci.yml` — self-test that calls lint.yml on this repo
- `action.yml` — composite action (setup-only, used internally or for advanced consumers)
- `lint-configs-626465/` — all linter configs (copied to workspace at runtime)
- `lint-configs-626465/.pre-commit-config.yaml` — source of truth for all pre-commit hooks
- `scripts/hooks/` — custom hook scripts referenced by pre-commit config
- `examples/` — example consumer workflow + override file

## Override mechanism

Consumer repos can:

1. **Skip groups** — via `skip-hooks` workflow input or `.coding-standards.yml` in repo root
2. **Override linter configs** — drop their own `.yamllint`, `.gitleaks.toml`, etc. The workflow won't overwrite existing files.

The `.pre-commit-config.yaml` always comes from this repo (it defines which hooks run).

## Adding a new config

1. Add the file to `lint-configs-626465/`
2. Add it to the `configs` array in `.github/workflows/lint.yml` (the "Apply coding-standards configs" step)
3. Update the README tables

## Adding a custom hook

1. Create `scripts/hooks/{name}` — executable, with comments explaining the rule
2. Add the hook entry to `lint-configs-626465/.pre-commit-config.yaml` with `entry: scripts/hooks/{name}`, `language: system`

## CI self-test

`.github/workflows/ci.yml` calls `./.github/workflows/lint.yml` (local ref) to test the workflow against this repo. If CI passes, the workflow works.
