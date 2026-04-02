# Getting to green CI

First run will find many issues. Strategy: fix what's auto-fixable, suppress the rest, clean up over time.

## Step 1 — Auto-fix

```bash
just cs-fix
```

## Step 2 — Python (ruff)

```bash
uvx ruff check --fix .
uvx ruff check --add-noqa .
```

## Step 3 — Shell (shellcheck)

No auto-fix. Replace `[ ]` with `[[ ]]`, quote variables, etc.
Add `# shellcheck disable=SC2086` for specific lines.

## Step 4 — Review what's left

```bash
just cs-lint 2>&1 | grep "❌"
```

Each `# noqa` / `# shellcheck disable` is a visible TODO.
Clean them up over time — the count is a health metric.
