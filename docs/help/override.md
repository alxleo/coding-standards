# Overriding any linter's config

Set `<LINTER>_CONFIG_FILE` in your `.mega-linter.yml`:

```yaml
PYTHON_RUFF_CONFIG_FILE: ruff.toml
YAML_YAMLLINT_CONFIG_FILE: .yamllint
REPOSITORY_GITLEAKS_CONFIG_FILE: .gitleaks.toml
ANSIBLE_ANSIBLE_LINT_CONFIG_FILE: .ansible-lint
PYTHON_PYRIGHT_CONFIG_FILE: pyrightconfig.json
```

Your file takes precedence over the baked config.

Run `just cs-show-config` to see what each linter uses.
