# coding-standards — dev tasks for this repo only.
# Consumers use the GitHub Action, not this justfile.

set unstable := true

[doc('Validate action.yml syntax')]
[group('lint')]
lint-action:
    python3 -c "import yaml; yaml.safe_load(open('action.yml'))"
