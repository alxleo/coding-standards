# Suppressing specific findings

## Inline (per-line)

```
Python (ruff):     # noqa: E501
Semgrep:           # nosemgrep: coding-standards.rule-name
Shellcheck:        # shellcheck disable=SC2086
Type ignore:       # type: ignore[arg-type]
```

## File-level

```
Trivy:     .trivyignore          (CVE IDs)
Gitleaks:  .gitleaksignore       (path patterns)
Codespell: .codespellrc          (word whitelist)
```

## Disable a linter entirely

```yaml
# .mega-linter.yml
DISABLE_LINTERS:
  - TERRAFORM_TFLINT
```

## Demote to warning (won't block CI)

```yaml
DISABLE_ERRORS_LINTERS:
  - PYTHON_PYRIGHT
```
