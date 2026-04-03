# Rule Catalog

Structured rule data for every configurable tool in the image. Generated at build time from CLI introspection, YAML parsing, and upstream documentation.

## Quick reference

```
just cs-catalog-rules                     All tools, markdown
just cs-catalog-rules --tool hadolint     Single tool
just cs-catalog-rules --format json       Machine-readable
just cs-catalog-rules --tool ruff --format json   Combine filters
```

## What's included

| Tool | Rules | Source |
|------|-------|--------|
| ruff | ~950 | `ruff rule --all --output-format json` |
| semgrep | ~30 | Custom rules from `semgrep-rules/*.yml` |
| hadolint | ~70 | GitHub wiki (DL-prefixed Dockerfile rules) |
| shellcheck | ~520 | shellcheck.net wiki sitemap |
| dockle | 20 | CIS Docker Benchmark checkpoints |

## Severity normalization

All tools map to four levels: `error`, `warning`, `info`, `ignore`.

- **error** — blocks the build (deny, error, fatal)
- **warning** — blocks under our `failure-threshold: warning` baseline
- **info** — advisory, reported but not blocking
- **ignore** — disabled by default, opt-in only

## Looking up a specific rule

Machine-readable output + jq:

```bash
# Find a hadolint rule
just cs-catalog-rules --tool hadolint --format json | jq '.hadolint.rules[] | select(.id == "DL3057")'

# All fixable ruff rules
just cs-catalog-rules --tool ruff --format json | jq '[.ruff.rules[] | select(.fixable == true)] | length'

# Search by keyword
just cs-catalog-rules --format json | jq '.. | objects | select(.summary? // "" | test("root"; "i"))'
```

## How it's generated

`scripts/generate_rule_catalog.py` runs at Docker build time. It:

1. Calls `ruff rule --all` (CLI introspection)
2. Parses `semgrep-rules/*.yml` (structured YAML)
3. Shallow-clones the hadolint wiki (one `git clone`, parses markdown headings)
4. Fetches shellcheck.net/wiki sitemap (one HTTP request, parses HTML)
5. Uses hardcoded dockle checkpoints (stable, ~20 checks)

Output: `/opt/coding-standards/rule-catalog.json` in the image.

Tool versions are extracted from the Dockerfile (`HADOLINT_VERSION`, `SHELLCHECK_VERSION`, etc.) so the catalog matches the installed binaries.
