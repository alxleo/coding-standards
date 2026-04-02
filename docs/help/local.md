# Running locally

The image supports native arm64 — no Rosetta on Apple Silicon:

```bash
just cs-lint
```

## Faster iteration — run tools directly

```bash
uvx ruff check .
uvx semgrep scan --config .semgrep/ .
shellcheck scripts/*.sh
```

## Pin to a specific version

```bash
just --set cs-image ghcr.io/alxleo/coding-standards:v1.8 cs-lint
```
