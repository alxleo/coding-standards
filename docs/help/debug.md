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
