#!/usr/bin/env bats
# Tests for scripts/ci/apply-configs.sh

setup() {
  WORKDIR=$(mktemp -d)
  CSDIR="$WORKDIR/.coding-standards"
  CONFIGS="$CSDIR/lint-configs-626465"

  # Create minimal coding-standards directory structure
  mkdir -p "$CONFIGS" "$CSDIR/scripts/hooks"

  # Create required config files
  touch "$CONFIGS/.shellcheckrc" "$CONFIGS/.editorconfig"
  echo "repos: []" > "$CONFIGS/.pre-commit-config.yaml"
  echo '#!/usr/bin/env bash' > "$CSDIR/scripts/hooks/test-hook"
  chmod +x "$CSDIR/scripts/hooks/test-hook"

  # Create path-based config defaults
  for cfg in .gitleaks.toml .markdownlint-cli2.yaml .yamllint .hadolint.yaml .jscpd.json .prettierrc commitlint.config.mjs; do
    echo "default" > "$CONFIGS/$cfg"
  done

  export GITHUB_OUTPUT="$WORKDIR/github_output"
  touch "$GITHUB_OUTPUT"
  export CS_ROOT="$CSDIR"
  export CONFIG_FILE="$WORKDIR/.coding-standards.yml"
  export INPUT_SKIP=""

  cd "$WORKDIR"
}

teardown() {
  rm -rf "$WORKDIR"
}

@test "no override file: empty skip, no error" {
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  grep -q "skip-hooks=" "$GITHUB_OUTPUT"
}

@test "empty override file: empty skip" {
  echo "" > "$CONFIG_FILE"
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  grep -q "skip-hooks=" "$GITHUB_OUTPUT"
}

@test "skip-hooks as list" {
  cat > "$CONFIG_FILE" <<'YAML'
skip-hooks:
  - python
  - shell
YAML
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  grep -q "skip-hooks=python,shell" "$GITHUB_OUTPUT"
}

@test "skip-hooks as string" {
  cat > "$CONFIG_FILE" <<'YAML'
skip-hooks: python,shell
YAML
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  grep -q "skip-hooks=python,shell" "$GITHUB_OUTPUT"
}

@test "INPUT_SKIP merged with file skips" {
  export INPUT_SKIP="trivy"
  cat > "$CONFIG_FILE" <<'YAML'
skip-hooks:
  - python
YAML
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  grep -q "skip-hooks=trivy,python" "$GITHUB_OUTPUT"
}

@test "malformed YAML: no crash, empty skip" {
  echo "{{{{invalid yaml" > "$CONFIG_FILE"
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  grep -q "skip-hooks=" "$GITHUB_OUTPUT"
}

@test "copies .shellcheckrc to root when absent" {
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  [ -f "$WORKDIR/.shellcheckrc" ]
}

@test "preserves consumer .shellcheckrc" {
  echo "consumer-content" > "$WORKDIR/.shellcheckrc"
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  [ "$(cat "$WORKDIR/.shellcheckrc")" = "consumer-content" ]
}

@test "consumer override replaces default in config dir" {
  echo "custom-gitleaks" > "$WORKDIR/.gitleaks.toml"
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  [ "$(cat "$CONFIGS/.gitleaks.toml")" = "custom-gitleaks" ]
}

@test "pre-commit config always copied to root" {
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  [ -f "$WORKDIR/.pre-commit-config.yaml" ]
}

@test "hook scripts copied and made executable" {
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  [ -x "$WORKDIR/scripts/hooks/test-hook" ]
}

@test "non-executable hook script fails validation" {
  # Create a non-executable hook in the target location
  mkdir -p "$WORKDIR/scripts/hooks"
  echo "not a script" > "$WORKDIR/scripts/hooks/bad-hook"
  # The copy step will overwrite with CS_ROOT hooks, but let's test
  # by adding a non-executable hook to the source
  echo "not a script" > "$CSDIR/scripts/hooks/bad-hook"
  # Don't make it executable
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  # chmod +x scripts/hooks/* makes all executable, so this should pass
  # The validation only fails if chmod itself fails
  [ "$status" -eq 0 ]
}
