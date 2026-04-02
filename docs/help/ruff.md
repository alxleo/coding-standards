# Overriding Python (ruff) config

## Extend the baseline

```toml
# ruff.toml
extend = ".mega-linter-config/ruff.toml"
[lint]
select = ["ALL"]
```

## Full replacement

```toml
# ruff.toml — your own, no extend
```

Set in `.mega-linter.yml`:

```yaml
PYTHON_RUFF_CONFIG_FILE: ruff.toml
```

## Migration recipe

```bash
uvx ruff check --fix . && uvx ruff check --add-noqa .
```
