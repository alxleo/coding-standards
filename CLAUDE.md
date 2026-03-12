# coding-standards

**Project class: GitHub Action** — a composite action consumed by other repos via `uses: alxleo/coding-standards@v1`. The product is centralized linting that runs in CI, not on developer machines.

This repo contains **no repo lists, no secrets, no private information**. It is a public linting action.

## How it works

Consumer repos add a ~6-line workflow stub. The action:

1. Installs Python, Node.js, pre-commit (all cached)
2. Copies baked-in linter configs into the workspace (skips files that already exist)
3. Copies custom hook scripts into `scripts/hooks/`
4. Runs `pre-commit run --all-files`

## Key files

- `action.yml` — composite action entry point
- `lint-configs-626465/` — all linter configs (baked into the action, copied to workspace at runtime)
- `lint-configs-626465/.pre-commit-config.yaml` — source of truth for all pre-commit hooks
- `scripts/hooks/` — custom hook scripts referenced by pre-commit config
- `examples/` — example consumer workflow + override file

## Override mechanism

Consumer repos can:

1. **Skip hooks** — via `skip-hooks` action input or `.coding-standards.yml` in repo root
2. **Override linter configs** — drop their own `.yamllint`, `.gitleaks.toml`, etc. The action won't overwrite existing files.

The `.pre-commit-config.yaml` always comes from this action (it defines which hooks run).

## Adding a new config

1. Add the file to `lint-configs-626465/`
2. Add it to the `configs` array in `action.yml` (the "Apply coding-standards configs" step)
3. Update the README tables

## Adding a custom hook

1. Create `scripts/hooks/{name}` — executable, with comments explaining the rule
2. Add the hook entry to `lint-configs-626465/.pre-commit-config.yaml` with `entry: scripts/hooks/{name}`, `language: system`

## CI self-test

`.github/workflows/ci.yml` uses `./` (local path) to test the action against this repo. If CI passes, the action works.
