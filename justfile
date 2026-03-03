set unstable := true

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
    output=$(bats tests/test-git-hooks.bats --print-output-on-failure 2>&1)
    status=$?
    if [ $status -ne 0 ]; then
        echo "$output"
        exit 1
    fi
    total=$(echo "$output" | grep -c '^ok ')
    echo "test-git-hooks: ${total} passed"

[doc('Run pre-commit on all files')]
[group('lint')]
lint:
    uvx pre-commit run --all-files

[doc('Install pre-commit + custom git hooks')]
[group('setup')]
setup:
    bash scripts/setup-hooks.sh

[doc('Remove cruft files and stale test branches')]
[group('maintenance')]
clean:
    find . -not -path "./.git/*" -not -path "./tests/fixtures/*" \( -name "*.del" -o -name "*.bak" -o -name "*.old" -o -name "*.tmp" -o -name "*.orig" \) -delete -print
    -git branch -D test/hook-validation 2>/dev/null
