# Recommended .gitignore entries

```gitignore
# coding-standards lint artifacts
megalinter-reports/
repo-manifest.json
.lycheecache
.ruff_cache/
.editorconfig           # only if you don't have your own
```

Run `just cs-init` to add these automatically.
