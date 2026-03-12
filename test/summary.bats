#!/usr/bin/env bats
# Tests for scripts/ci/summary.sh

setup() {
  export LINT_LOG_DIR=$(mktemp -d)
  export GITHUB_STEP_SUMMARY="$LINT_LOG_DIR/step_summary.md"
}

teardown() {
  rm -rf "$LINT_LOG_DIR"
}

create_outcomes() {
  local default_outcome="$1"
  for group in hygiene cruft gitleaks typos yaml actions markdown \
               commitlint python shell justfile jscpd trivy semgrep; do
    echo "$default_outcome" > "$LINT_LOG_DIR/${group}.outcome"
  done
}

@test "all pass: exits 0" {
  create_outcomes success
  run scripts/ci/summary.sh
  [ "$status" -eq 0 ]
  [[ "$output" == *"All checks passed"* ]]
}

@test "all pass: step summary shows checkmark" {
  create_outcomes success
  run scripts/ci/summary.sh
  grep -q "white_check_mark" "$GITHUB_STEP_SUMMARY"
}

@test "one failure: exits 1" {
  create_outcomes success
  echo "failure" > "$LINT_LOG_DIR/hygiene.outcome"
  run scripts/ci/summary.sh
  [ "$status" -eq 1 ]
  [[ "$output" == *"FAIL"* ]]
}

@test "failure: step summary shows failure table" {
  create_outcomes success
  echo "failure" > "$LINT_LOG_DIR/python.outcome"
  echo "src/main.py:1:1: E302 expected 2 blank lines" > "$LINT_LOG_DIR/python.log"
  run scripts/ci/summary.sh
  [ "$status" -eq 1 ]
  grep -q "failures detected" "$GITHUB_STEP_SUMMARY"
  grep -q "Python" "$GITHUB_STEP_SUMMARY"
}

@test "skipped groups show skip" {
  create_outcomes success
  rm "$LINT_LOG_DIR/extra.outcome" 2>/dev/null || true
  # extra is not in the outcome files, so it defaults to skipped
  run scripts/ci/summary.sh
  [[ "$output" == *"skip"* ]]
}

@test "failure with log: shows error detail" {
  create_outcomes success
  echo "failure" > "$LINT_LOG_DIR/yaml.outcome"
  echo "ERROR: config.yml:3:1 wrong indentation" > "$LINT_LOG_DIR/yaml.log"
  run scripts/ci/summary.sh
  [ "$status" -eq 1 ]
  [[ "$output" == *"↳"* ]]
}

@test "no GITHUB_STEP_SUMMARY: still works" {
  create_outcomes success
  unset GITHUB_STEP_SUMMARY
  run scripts/ci/summary.sh
  [ "$status" -eq 0 ]
}
