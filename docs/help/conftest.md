# Adding custom conftest/Rego policies

Add `policy/` + `conftest.toml` in your repo. Policies run alongside the baked repo-standards and compose policies automatically.

```rego
# policy/compose/resources.rego
package compose.resources
import rego.v1
deny contains msg if {
    some name, svc in input.services
    not svc.deploy.resources.limits.memory
    msg := sprintf("service '%s' missing memory limit", [name])
}
```

```
echo 'parser = "yaml"' > conftest.toml
```

## Extend baked repo-standards

Promote warnings to blocking errors in your repo:

```rego
# policy/repo-standards/local.rego
package repo_standards.local
import data.repo_standards.python
deny := python.warn
```
