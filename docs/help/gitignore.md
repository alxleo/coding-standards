# Recommended .gitignore entries

```gitignore
# coding-standards lint artifacts
.mega-linter-config/
megalinter-reports/
repo-manifest.json
.lycheecache
.ruff_cache/
.editorconfig           # only if you don't have your own
.v8rrc.yml              # symlink to .mega-linter-config/
```

Run `just cs-init` to add these automatically.
