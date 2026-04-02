# Disabling linters

In your `.mega-linter.yml`:

```yaml
DISABLE_LINTERS:
  - TERRAFORM_TFLINT       # no terraform files
  - ANSIBLE_ANSIBLE_LINT   # no ansible playbooks
  - KUBERNETES_KUBECONFORM # no k8s manifests
  - REPOSITORY_KNIP       # no JS/TS project
  - TYPESCRIPT_TSC        # no TypeScript
  - SQL_SQLFLUFF          # no SQL files
```

Linters auto-activate on file detection, so most won't run even without disabling. Explicit disable is for faster runs and cleaner output.

## Demote to warning

Still runs, won't block CI:

```yaml
DISABLE_ERRORS_LINTERS:
  - PYTHON_PYRIGHT        # type errors are advisory
```
