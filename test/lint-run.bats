#!/usr/bin/env bats
# Tests for scripts/ci/lint-run.sh

setup() {
  export LINT_LOG_DIR=$(mktemp -d)
}

teardown() {
  rm -rf "$LINT_LOG_DIR"
}

@test "records success outcome on exit 0" {
  run scripts/ci/lint-run.sh test-pass true
  [ "$status" -eq 0 ]
  [ "$(cat "$LINT_LOG_DIR/test-pass.outcome")" = "success" ]
}

@test "records failure outcome on exit 1" {
  run scripts/ci/lint-run.sh test-fail false
  [ "$status" -ne 0 ]
  [ "$(cat "$LINT_LOG_DIR/test-fail.outcome")" = "failure" ]
}

@test "creates log file" {
  run scripts/ci/lint-run.sh test-log echo "hello world"
  [ "$status" -eq 0 ]
  [ -f "$LINT_LOG_DIR/test-log.log" ]
  grep -q "hello world" "$LINT_LOG_DIR/test-log.log"
}

@test "captures stderr in log" {
  run scripts/ci/lint-run.sh test-stderr bash -c 'echo "err" >&2'
  [ -f "$LINT_LOG_DIR/test-stderr.log" ]
  grep -q "err" "$LINT_LOG_DIR/test-stderr.log"
}

@test "emits ::error annotations for file:line:col patterns" {
  run scripts/ci/lint-run.sh test-annot bash -c 'echo "src/main.py:42:5: undefined name foo"; exit 1'
  [ "$status" -ne 0 ]
  [[ "$output" == *"::error file=src/main.py,line=42"* ]]
}

@test "propagates exact exit code" {
  run scripts/ci/lint-run.sh test-exit bash -c 'exit 2'
  [ "$status" -eq 2 ]
  [ "$(cat "$LINT_LOG_DIR/test-exit.outcome")" = "failure" ]
}
