# Overriding Python (ruff) config

## Repository config

```toml
# quality/lint/ruff.toml
[lint]
select = ["ALL"]
```

Select the shared config directory in `.mega-linter.yml`:

```yaml
LINTER_RULES_PATH: quality/lint
```

The filename already matches the baseline default, so no Ruff-specific
MegaLinter setting is required. This repository config replaces the baked Ruff
baseline.

## Migration recipe

```bash
uvx ruff check --fix . && uvx ruff check --add-noqa .
```
