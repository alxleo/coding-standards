#!/usr/bin/env bats
# Tests for custom git hook wrappers.
# Each test runs in a throwaway git repo with a minimal pre-commit config.

load 'test_helper/bats-support/load'
load 'test_helper/bats-assert/load'

setup() {
    # Resolve repo root from this test file's location
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
    export REPO_ROOT

    SANDBOX=$(mktemp -d)
    trap 'rm -rf "$SANDBOX"' EXIT
    cd "$SANDBOX"
    git init --initial-branch=main >/dev/null 2>&1
    git config user.email "test@test.com"
    git config user.name "Test"

    # Minimal pre-commit config
    cat > .pre-commit-config.yaml <<'YAML'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
  - repo: https://github.com/alessandrojcm/commitlint-pre-commit-hook
    rev: v9.21.0
    hooks:
      - id: commitlint
        stages: [commit-msg]
        additional_dependencies: ['@commitlint/config-conventional']
YAML

    cat > commitlint.config.mjs <<'JS'
export default { extends: ['@commitlint/config-conventional'] };
JS

    # Copy scripts under test
    mkdir -p scripts
    cp "$REPO_ROOT/scripts/setup-hooks.sh" scripts/
    cp "$REPO_ROOT/scripts/git-pre-commit.sh" scripts/
    cp "$REPO_ROOT/scripts/git-commit-msg.sh" scripts/
    cp "$REPO_ROOT/scripts/git-post-commit.sh" scripts/
    cp "$REPO_ROOT/scripts/git-pre-push.sh" scripts/
    chmod +x scripts/*.sh

    git add -A
    git commit --no-verify -m "initial" >/dev/null 2>&1
}

teardown() {
    rm -rf "$SANDBOX"
}

# ── setup-hooks.sh ───────────────────────────────────────────

@test "setup-hooks: installs all four hook files" {
    bash scripts/setup-hooks.sh
    assert [ -f .git/hooks/pre-commit ]
    assert [ -f .git/hooks/commit-msg ]
    assert [ -f .git/hooks/post-commit ]
    assert [ -f .git/hooks/pre-push ]
}

@test "setup-hooks: hooks are executable" {
    bash scripts/setup-hooks.sh
    assert [ -x .git/hooks/pre-commit ]
    assert [ -x .git/hooks/commit-msg ]
    assert [ -x .git/hooks/post-commit ]
    assert [ -x .git/hooks/pre-push ]
}

@test "setup-hooks: idempotent on second run" {
    bash scripts/setup-hooks.sh
    run bash scripts/setup-hooks.sh
    assert_success
}

@test "setup-hooks: prints orientation with hook descriptions" {
    run bash scripts/setup-hooks.sh
    assert_success
    assert_output --partial "pre-commit"
    assert_output --partial "commit-msg"
    assert_output --partial "post-commit"
    assert_output --partial "pre-push"
    assert_output --partial "Lint staged files"
    assert_output --partial "compact-run"
}

# ── git-pre-commit.sh ───────────────────────────────────────

@test "pre-commit: quiet on success" {
    bash scripts/setup-hooks.sh >/dev/null 2>&1
    printf "clean file\n" > clean.txt
    git add clean.txt
    run bash .git/hooks/pre-commit
    assert_success
    assert_output --partial "pre-commit passed"
    refute_output --partial "end-of-file-fixer"
    refute_output --partial "trailing-whitespace"
}

@test "pre-commit: loud on failure" {
    bash scripts/setup-hooks.sh >/dev/null 2>&1
    printf "trailing spaces   \n" > dirty.txt
    git add dirty.txt
    run bash .git/hooks/pre-commit
    assert_failure
    assert_output --partial "pre-commit failed"
    assert_output --partial "trailing-whitespace"
}

# ── git-commit-msg.sh ───────────────────────────────────────

@test "commit-msg: quiet on valid conventional commit" {
    bash scripts/setup-hooks.sh >/dev/null 2>&1
    echo "feat: valid commit message" > .git/COMMIT_EDITMSG
    run bash .git/hooks/commit-msg .git/COMMIT_EDITMSG
    assert_success
    assert_output --partial "commit-msg passed"
}

@test "commit-msg: loud on invalid message" {
    bash scripts/setup-hooks.sh >/dev/null 2>&1
    echo "bad message no prefix" > .git/COMMIT_EDITMSG
    run bash .git/hooks/commit-msg .git/COMMIT_EDITMSG
    assert_failure
    assert_output --partial "commit-msg failed"
}

# ── git-post-commit.sh ──────────────────────────────────────

@test "post-commit: removes .del .bak .old .tmp .orig files" {
    touch cruft1.del cruft2.bak cruft3.old cruft4.tmp cruft5.orig
    run bash scripts/git-post-commit.sh
    assert_success
    assert [ ! -f cruft1.del ]
    assert [ ! -f cruft2.bak ]
    assert [ ! -f cruft3.old ]
    assert [ ! -f cruft4.tmp ]
    assert [ ! -f cruft5.orig ]
    assert_output --partial "cruft file(s)"
}

@test "post-commit: preserves non-cruft files" {
    touch keep.txt cruft.del
    bash scripts/git-post-commit.sh >/dev/null 2>&1
    assert [ -f keep.txt ]
}

@test "post-commit: removes empty directories" {
    mkdir -p empty-dir/nested
    bash scripts/git-post-commit.sh >/dev/null 2>&1
    assert [ ! -d empty-dir ]
}

@test "post-commit: silent when nothing to clean" {
    run bash scripts/git-post-commit.sh
    assert_success
    refute_output --partial "cruft"
}

@test "post-commit: skips git-tracked cruft files" {
    echo "intentional" > tracked.bak
    git add tracked.bak
    git commit --no-verify -m "fix: add tracked bak" >/dev/null 2>&1
    bash scripts/git-post-commit.sh >/dev/null 2>&1
    assert [ -f tracked.bak ]
}

@test "post-commit: skips .git directory" {
    touch .git/test-safety.tmp
    bash scripts/git-post-commit.sh >/dev/null 2>&1
    assert [ -f .git/test-safety.tmp ]
    rm -f .git/test-safety.tmp
}

# ── git-pre-push.sh ─────────────────────────────────────────

@test "pre-push: blocks direct push to main" {
    run bash -c 'echo "refs/heads/main abc123 refs/heads/main def456" | bash scripts/git-pre-push.sh origin'
    assert_failure
    assert_output --partial "Direct push to main is blocked"
}

@test "pre-push: allows push to non-main branch" {
    run bash -c 'echo "refs/heads/feature abc123 refs/heads/feature def456" | bash scripts/git-pre-push.sh origin'
    assert_output --partial "Running pre-push validation"
}

@test "pre-push: allows delete push (zero SHA)" {
    run bash -c 'echo "refs/heads/main 0000000000000000000000000000000000000000 refs/heads/main def456" | bash scripts/git-pre-push.sh origin'
    refute_output --partial "Direct push to main is blocked"
}

# ── .envrc.snippet ───────────────────────────────────────────

@test "envrc snippet: installs hooks when post-commit missing" {
    assert [ ! -f .git/hooks/post-commit ]
    bash -c "source $REPO_ROOT/configs/.envrc.snippet"
    assert [ -f .git/hooks/post-commit ]
}

@test "envrc snippet: skips when already installed" {
    bash scripts/setup-hooks.sh >/dev/null 2>&1
    local before after
    before=$(shasum -a 256 .git/hooks/post-commit | cut -d' ' -f1)
    bash -c "source $REPO_ROOT/configs/.envrc.snippet"
    after=$(shasum -a 256 .git/hooks/post-commit | cut -d' ' -f1)
    assert_equal "$before" "$after"
}
