# Troubleshooting a failing linter

## 1. See what config each linter uses

```bash
just cs-show-config
```

## 2. Run a single linter to isolate

```bash
just cs-lint-one PYTHON_RUFF
```

## 3. Read the detailed log

```bash
cat megalinter-reports/linters_logs/PYTHON_RUFF-*.log
```

## 4. Run the tool directly (same version as image)

```bash
docker run --rm -v .:/tmp/lint --entrypoint ruff \
  ghcr.io/alxleo/coding-standards:latest \
  check /tmp/lint
```

## 5. Check config override

```bash
just cs-show-config | grep RUFF
```

## Common issues

| Message | Cause |
|---------|-------|
| "no files to lint" | Linter auto-skipped (no matching files) |
| "config not found" | Check `_CONFIG_FILE` path in `.mega-linter.yml` |
| "command not found" | Tool missing from image (file an issue) |

## Token and Gitea troubleshooting

CI runs offline by default — no token needed. This section is for consumers who opt into online checks (scheduled workflows, Gitea runners with GitHub PATs).

### zizmor says 401 but GITHUB_TOKEN is set

**Cause**: MegaLinter silently replaces env var values with `HIDDEN_BY_MEGALINTER` before passing to linters. Your token exists in the container but zizmor never sees it.

**Diagnose**: check if MegaLinter replaced the token:
```bash
docker run --rm -v .:/tmp/lint -e GITHUB_TOKEN=$GITHUB_TOKEN \
  ghcr.io/alxleo/coding-standards:latest \
  bash -c 'case "$GITHUB_TOKEN" in HIDDEN_BY*) echo "HIDDEN";; "") echo "EMPTY";; *) echo "PRESENT";; esac'
```
If it prints `HIDDEN` — MegaLinter replaced the value with `HIDDEN_BY_MEGALINTER`.

**Fix**: add to your `.mega-linter.yml`:
```yaml
REPOSITORY_ZIZMOR_UNSECURED_ENV_VARIABLES: GITHUB_TOKEN
```

### Pushed a fix to the action but Gitea runner uses the old version

**Cause**: act_runner caches action refs. `@main` resolves to a SHA on first use and never re-fetches. Your fix is on GitHub but the runner has the old SHA cached.

**Fix**: restart the act_runner container, or pin to the specific commit SHA instead of `@main`.

### GitHub Actions GITHUB_TOKEN gets 401 on public repos

**Cause**: GitHub's scoped GITHUB_TOKEN only works against the current repo. `git-upload-pack` to other repos (e.g., `actions/checkout.git`) fails with 401 — worse than no token at all, because anonymous access works fine for public repos.

**Fix**: don't pass `GITHUB_TOKEN` on GitHub Actions. The default (no token) uses anonymous access which works for public repos. Only pass a token on Gitea where `REAL_GITHUB_TOKEN` is a real PAT.

Consumer pattern:
```yaml
- run: |
    [ -n "$REAL_GITHUB_TOKEN" ] && \
      echo "GITHUB_TOKEN=$REAL_GITHUB_TOKEN" > .megalinter.env
```

### Composite action paths differ between GitHub and Gitea

**Cause**: `${{ github.workspace }}` (expression context) and `$GITHUB_WORKSPACE` (shell env var) resolve to different paths on Gitea runners. The expression resolves in the job container context; the shell var resolves in the step's execution context.

**Fix**: already handled in the docker-action. If writing custom composite actions for Gitea, use shell env vars (`$GITHUB_WORKSPACE`) not expression context (`${{ github.workspace }}`).
