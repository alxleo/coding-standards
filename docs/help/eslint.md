# Overriding JS/TS (ESLint) config

Add `eslint.config.mjs` to your repo root.

Set in `.mega-linter.yml`:

```yaml
JAVASCRIPT_ES_CONFIG_FILE: eslint.config.mjs
TYPESCRIPT_ES_CONFIG_FILE: eslint.config.mjs
```

The baked config includes: unicorn, security, sonarjs, i18next plugins. Your config fully replaces it — import what you need.
