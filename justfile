set unstable := true

[doc('Run all tests')]
[group('test')]
test: test-hooks test-git-hooks

[doc('Run pre-commit hook negative tests')]
[group('test')]
test-hooks:
    bash tests/test-hooks.sh

[doc('Run git hook wrapper tests (bats)')]
[group('test')]
test-git-hooks:
    bats tests/test-git-hooks.bats

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
