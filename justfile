# Dev justfile — extends consumer justfile with test tasks.
# Consumer tasks (setup, doctor, lint, clean) live in configs/justfile.

import 'configs/justfile'

[doc('Verify sync-manifest.yml covers all managed files')]
[group('lint')]
check-manifest:
    uv run --with pyyaml scripts/check-manifest-coverage.py

[doc('Verify remote pre-commit config is up to date')]
[group('lint')]
check-remote-config:
    uv run scripts/generate-remote-config.py --check

[doc('Regenerate remote pre-commit config from baseline')]
[group('lint')]
generate-remote-config:
    uv run scripts/generate-remote-config.py

[doc('Run all tests (quiet on success)')]
[group('test')]
test: test-hooks test-git-hooks

[doc('Run pre-commit hook negative tests')]
[group('test')]
test-hooks:
    #!/usr/bin/env bash
    output=$(bash tests/test-hooks.sh 2>&1)
    status=$?
    if [ $status -ne 0 ]; then
        echo "$output"
        exit 1
    fi
    passed=$(echo "$output" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+')
    echo "test-hooks: ${passed} passed"

[doc('Run git hook wrapper tests (bats)')]
[group('test')]
test-git-hooks:
    #!/usr/bin/env bash
    output=$(bats tests/test-doctor.bats tests/test-compact-run.bats tests/test-git-hooks.bats tests/test-manifest.bats --print-output-on-failure 2>&1)
    status=$?
    if [ $status -ne 0 ]; then
        echo "$output"
        exit 1
    fi
    total=$(echo "$output" | grep -c '^ok ')
    echo "test-git-hooks: ${total} passed"
