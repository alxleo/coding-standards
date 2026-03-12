#!/usr/bin/env bats
# Tests for scripts/ci/report-statuses.sh
# Mocks curl to avoid real API calls.

setup() {
  export LINT_LOG_DIR=$(mktemp -d)
  export MOCK_DIR=$(mktemp -d)
  export CURL_LOG="$MOCK_DIR/curl_calls.log"
  touch "$CURL_LOG"

  # Required env vars
  export GH_TOKEN="test-token"
  export SHA="abc123"
  export API_URL="https://api.example.com"
  export REPO="test/repo"
  export RUN_URL="https://example.com/run/1"
  export RUN_ID="1"

  # Create mock curl that logs calls and always succeeds
  cat > "$MOCK_DIR/curl" <<'MOCK'
#!/usr/bin/env bash
echo "$@" >> "$CURL_LOG"
if [[ "$*" == *"actions/runs"* ]]; then
  echo '{"jobs":[]}'
fi
exit 0
MOCK
  chmod +x "$MOCK_DIR/curl"

  # Create mock uv that passes through to python3
  cat > "$MOCK_DIR/uv" <<'MOCK'
#!/usr/bin/env bash
if [[ "$1" == "run" ]]; then
  shift
  while [[ "$1" == --* ]]; do shift; done
  exec "$@"
fi
MOCK
  chmod +x "$MOCK_DIR/uv"

  export PATH="$MOCK_DIR:$PATH"
}

teardown() {
  rm -rf "$LINT_LOG_DIR" "$MOCK_DIR"
}

@test "posts success status for passing group" {
  echo "success" > "$LINT_LOG_DIR/python.outcome"
  run scripts/ci/report-statuses.sh
  [ "$status" -eq 0 ]
  grep -q "statuses/abc123" "$CURL_LOG"
  grep -q '"success"' "$CURL_LOG"
  grep -q "coding-standards: python" "$CURL_LOG"
}

@test "posts failure status with hint" {
  echo "failure" > "$LINT_LOG_DIR/yaml.outcome"
  echo "ERROR: bad indentation at line 5" > "$LINT_LOG_DIR/yaml.log"
  run scripts/ci/report-statuses.sh
  [ "$status" -eq 0 ]
  grep -q '"failure"' "$CURL_LOG"
  grep -q "bad indentation" "$CURL_LOG"
}

@test "skips groups without outcome files" {
  # No outcome files created — should not post any statuses
  run scripts/ci/report-statuses.sh
  [ "$status" -eq 0 ]
  [ ! -f "$CURL_LOG" ] || ! grep -q "statuses" "$CURL_LOG"
}

@test "failure without log: uses generic Failed" {
  echo "failure" > "$LINT_LOG_DIR/trivy.outcome"
  # No .log file
  run scripts/ci/report-statuses.sh
  [ "$status" -eq 0 ]
  grep -q "Failed" "$CURL_LOG"
}

@test "escapes double quotes in description" {
  echo "failure" > "$LINT_LOG_DIR/hygiene.outcome"
  echo 'Error: "bad" value found' > "$LINT_LOG_DIR/hygiene.log"
  run scripts/ci/report-statuses.sh
  [ "$status" -eq 0 ]
  # Should not crash from unescaped quotes
  grep -q "statuses" "$CURL_LOG"
}
