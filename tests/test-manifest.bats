#!/usr/bin/env bats
# Tests for sync-manifest coverage check.

load 'test_helper/bats-support/load'
load 'test_helper/bats-assert/load'

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
}

@test "check-manifest: passes with current files" {
    run uv run --with pyyaml "$REPO_ROOT/scripts/check-manifest-coverage.py"
    assert_success
    assert_output --partial "files, all covered"
}

@test "check-manifest: fails when file on disk has no manifest entry" {
    touch "$REPO_ROOT/configs/.test-orphan"
    run uv run --with pyyaml "$REPO_ROOT/scripts/check-manifest-coverage.py"
    rm -f "$REPO_ROOT/configs/.test-orphan"
    assert_failure
    assert_output --partial "NOT in sync-manifest.yml"
    assert_output --partial "configs/.test-orphan"
}

@test "check-manifest: fails when manifest entry has no file on disk" {
    cp "$REPO_ROOT/sync-manifest.yml" "$REPO_ROOT/sync-manifest.yml.bak"
    # Add a fake entry under configs
    sed -i '' 's/  justfile:.*/  justfile:                { sync: all }\n  ghost-file.txt:          { sync: all }/' "$REPO_ROOT/sync-manifest.yml"
    run uv run --with pyyaml "$REPO_ROOT/scripts/check-manifest-coverage.py"
    mv "$REPO_ROOT/sync-manifest.yml.bak" "$REPO_ROOT/sync-manifest.yml"
    assert_failure
    assert_output --partial "NOT on disk"
    assert_output --partial "configs/ghost-file.txt"
}
