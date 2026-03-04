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
    output=$(bats tests/test-doctor.bats tests/test-compact-run.bats tests/test-git-hooks.bats --print-output-on-failure 2>&1)
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

[doc('Check prerequisites for local development')]
[group('setup')]
doctor:
    #!/usr/bin/env bash
    ok=0; missing=0
    check() {
        local name="$1" cmd="$2"
        if command -v "$cmd" >/dev/null 2>&1; then
            ver=$("$cmd" --version 2>&1 | head -1 | grep -oE '[0-9]+\.[0-9]+[.0-9]*' | head -1)
            printf "  ✓ %-14s %s\n" "$name" "${ver:-installed}"
            ok=$((ok + 1))
        else
            printf "  ✗ %-14s missing\n" "$name"
            missing=$((missing + 1))
        fi
    }
    echo "Prerequisites:"
    check git git
    check uv uv
    check just just
    check bats bats
    echo ""
    echo "Pre-commit (via uvx):"
    if uvx pre-commit --version >/dev/null 2>&1; then
        ver=$(uvx pre-commit --version 2>&1 | grep -oE '[0-9]+\.[0-9]+[.0-9]*' | head -1)
        printf "  ✓ %-14s %s\n" "pre-commit" "$ver"
        ok=$((ok + 1))
    else
        printf "  ✗ %-14s uvx pre-commit not working\n" "pre-commit"
        missing=$((missing + 1))
    fi
    echo ""
    echo "$ok available, $missing missing"
    [ "$missing" -eq 0 ] || exit 1

[doc('Remove cruft files and stale test branches')]
[group('maintenance')]
clean:
    find . -not -path "./.git/*" -not -path "./tests/fixtures/*" \( -name "*.del" -o -name "*.bak" -o -name "*.old" -o -name "*.tmp" -o -name "*.orig" \) -delete -print
    -git branch -D test/hook-validation 2>/dev/null
