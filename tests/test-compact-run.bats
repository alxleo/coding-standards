#!/usr/bin/env bats
# Tests for compact-run — LLM-friendly command wrapper.

load 'test_helper/bats-support/load'
load 'test_helper/bats-assert/load'

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
    COMPACT="$REPO_ROOT/scripts/compact-run"
    chmod +x "$COMPACT"
}

# ── Success path ──────────────────────────────────────────────

@test "compact-run: success shows checkmark and line count" {
    run "$COMPACT" echo "hello"
    assert_success
    assert_output --regexp '✓ [0-9]+ lines \([0-9]+s\)'
}

@test "compact-run: preserves exit code 0 on success" {
    run "$COMPACT" true
    assert_success
}

# ── Failure path ──────────────────────────────────────────────

@test "compact-run: failure shows X and exit code" {
    run "$COMPACT" false
    assert_failure
    assert_output --regexp '✗ exit 1 — [0-9]+ lines \([0-9]+s\)'
}

@test "compact-run: preserves non-zero exit code" {
    run "$COMPACT" bash -c 'exit 42'
    assert_failure 42
}

# ── Threshold behavior ────────────────────────────────────────

@test "compact-run: shows full output when under threshold" {
    # Generate 5 lines of output, threshold defaults to 30
    run "$COMPACT" bash -c 'for i in $(seq 1 5); do echo "line $i"; done; exit 1'
    assert_failure
    assert_output --partial "line 1"
    assert_output --partial "line 5"
    refute_output --partial "more lines"
}

@test "compact-run: truncates output when over threshold" {
    # Generate 50 lines, threshold=30, max_lines=15
    run env COMPACT_THRESHOLD=30 COMPACT_LINES=15 \
        "$COMPACT" bash -c 'for i in $(seq 1 50); do echo "line $i"; done; exit 1'
    assert_failure
    assert_output --partial "line 1"
    assert_output --partial "line 15"
    refute_output --partial "line 16"
    assert_output --partial "more lines"
}

# ── COMPACT_LINES override ────────────────────────────────────

@test "compact-run: COMPACT_LINES controls inline line count" {
    run env COMPACT_THRESHOLD=5 COMPACT_LINES=3 \
        "$COMPACT" bash -c 'for i in $(seq 1 20); do echo "line $i"; done; exit 1'
    assert_failure
    assert_output --partial "line 3"
    refute_output --partial "line 4"
    assert_output --partial "17 more lines"
}

@test "compact-run: COMPACT_LINES larger than output does not go negative" {
    run env COMPACT_THRESHOLD=2 COMPACT_LINES=100 \
        "$COMPACT" bash -c 'for i in $(seq 1 5); do echo "line $i"; done; exit 1'
    assert_failure
    refute_output --partial -- "-"
    refute_output --partial "more lines"
}

# ── Empty args guard ──────────────────────────────────────────

@test "compact-run: exits with usage on empty invocation" {
    run "$COMPACT"
    assert_failure
    assert_output --partial "Usage:"
}
