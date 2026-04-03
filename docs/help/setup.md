# First-time setup

## 1. Add CI workflow

```yaml
# .github/workflows/lint.yml (or .gitea/workflows/)
name: Lint
on:
  push:
    branches: [main]
  pull_request:
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6
        with:
          fetch-depth: 0
      - uses: alxleo/coding-standards/docker-action@v1
```

Or run `just cs-init` to auto-generate this.

## 2. Add .gitignore entries

Run `just cs-help gitignore` for the list, or `just cs-init` adds them automatically.

## 3. Run locally

```bash
just cs-lint
```

## 4. Expect many findings on first run

See `just cs-help migrate` for the fast path to green CI.

## 5. Optional: scheduled checks

CI runs fully offline for speed. Network-dependent checks (zizmor pin verification, trivy CVE scanning) belong in a weekly scheduled workflow:

```yaml
# .github/workflows/scheduled.yml
name: Scheduled
on:
  schedule:
    - cron: "3 3 * * 1"  # Monday 03:03 UTC
  workflow_dispatch:
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6
      - name: Zizmor pin verification
        run: pipx run zizmor .
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## No .mega-linter.yml needed

The image works zero-config. Only create `.mega-linter.yml` if you need to customize (disable linters, override configs). See `just cs-help override`.
