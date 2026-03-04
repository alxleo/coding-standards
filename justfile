# Dev justfile — extends consumer justfile with test tasks.
# Consumer tasks (setup, doctor, lint, clean) live in configs/justfile.

set unstable := true

import 'configs/justfile'

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
    output=$(bats tests/test-doctor.bats tests/test-compact-run.bats tests/test-git-hooks.bats --print-output-on-failure 2>&1)
    status=$?
    if [ $status -ne 0 ]; then
        echo "$output"
        exit 1
    fi
    total=$(echo "$output" | grep -c '^ok ')
    echo "test-git-hooks: ${total} passed"
