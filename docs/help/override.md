# Overriding any linter's config

Put repository-owned configs in one directory and set it once:

```yaml
LINTER_RULES_PATH: quality/lint
```

Matching files take precedence over baked configs. If a filename differs from
the baseline default, declare only that override:

```yaml
ACTION_ACTIONLINT_CONFIG_FILE: actionlint.yaml
```

Run `just cs-show-config` to see what each linter uses.
