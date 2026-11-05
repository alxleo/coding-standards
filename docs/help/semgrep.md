# Adding custom semgrep rules

Drop a `.semgrep/` directory in your repo. The entrypoint auto-discovers it and runs alongside the baked rules.

```yaml
# .semgrep/my-rules.yml
rules:
  - id: no-hardcoded-api-key
    pattern: "api_key = \"...\""
    message: Use environment variables for API keys
    languages: [python]
    severity: ERROR
```

Your rule IDs get a `semgrep.` prefix from the directory (`semgrep.no-hardcoded-api-key`).

## Suppress a rule

Inline: `# nosemgrep: semgrep.no-hardcoded-api-key` (the bare `no-hardcoded-api-key` also works)

Via config (`.mega-linter.yml`):

```yaml
REPOSITORY_SEMGREP_ARGUMENTS:
  - --exclude-rule=rules.custom.coding-standards.rule-name
```

## Baked rule prefixes

```
rules.security-audit.<id>              OWASP/security rules
rules.trailofbits.<id>                 Audit rules
rules.custom.coding-standards.<id>     Our custom rules
```
