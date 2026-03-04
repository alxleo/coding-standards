#!/usr/bin/env bats
# Tests for `just doctor` prerequisites check.

load 'test_helper/bats-support/load'
load 'test_helper/bats-assert/load'

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
}

@test "doctor: reports installed tools with versions" {
    run just --justfile "$REPO_ROOT/justfile" doctor
    assert_success
    # git and just are guaranteed available (we're running in git via just)
    assert_output --partial "✓ git"
    assert_output --partial "✓ just"
    assert_output --partial "available"
}

@test "doctor: reports count format with available and missing" {
    run just --justfile "$REPO_ROOT/justfile" doctor
    assert_output --regexp '[0-9]+ available, [0-9]+ missing'
}

@test "doctor: output includes all expected tool names" {
    run just --justfile "$REPO_ROOT/justfile" doctor
    assert_output --partial "git"
    assert_output --partial "uv"
    assert_output --partial "just"
    assert_output --partial "bats"
    assert_output --partial "pre-commit"
}
