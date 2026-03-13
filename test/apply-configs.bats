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

  # Create baseline configs (extends-capable tools)
  echo "baseline-yamllint" > "$CONFIGS/.yamllint.baseline"
  echo "baseline-gitleaks" > "$CONFIGS/.gitleaks.baseline.toml"
  echo "baseline-markdownlint" > "$CONFIGS/.markdownlint-cli2.baseline.yaml"
  echo "baseline-commitlint" > "$CONFIGS/commitlint.config.baseline.mjs"

  # Create active configs (will be overwritten by apply-configs.sh)
  echo "active-yamllint" > "$CONFIGS/.yamllint"
  echo "active-gitleaks" > "$CONFIGS/.gitleaks.toml"
  echo "active-markdownlint" > "$CONFIGS/.markdownlint-cli2.yaml"
  echo "active-commitlint" > "$CONFIGS/commitlint.config.mjs"

  # Non-extends configs
  for cfg in .hadolint.yaml .jscpd.json .prettierrc; do
    echo "default-$cfg" > "$CONFIGS/$cfg"
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

# ── Skip parsing ─────────────────────────────────────

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

# ── Root configs (no --config support) ────────────────

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

@test "pre-commit config always copied to root" {
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  [ -f "$WORKDIR/.pre-commit-config.yaml" ]
}

# ── Extends-capable configs: no override ─────────────

@test "no override: yamllint uses baseline" {
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  [ "$(cat "$CONFIGS/.yamllint")" = "baseline-yamllint" ]
}

@test "no override: gitleaks uses baseline" {
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  [ "$(cat "$CONFIGS/.gitleaks.toml")" = "baseline-gitleaks" ]
}

# ── Extends-capable configs: with override ────────────

@test "yamllint override applied from .coding-standards.yml" {
  echo "consumer-yamllint-extends-baseline" > "$WORKDIR/.yamllint.local.yml"
  cat > "$CONFIG_FILE" <<'YAML'
overrides:
  yamllint: .yamllint.local.yml
YAML
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  [ "$(cat "$CONFIGS/.yamllint")" = "consumer-yamllint-extends-baseline" ]
}

@test "gitleaks override applied from .coding-standards.yml" {
  echo "consumer-gitleaks-extends-baseline" > "$WORKDIR/.gitleaks.local.toml"
  cat > "$CONFIG_FILE" <<'YAML'
overrides:
  gitleaks: .gitleaks.local.toml
YAML
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  [ "$(cat "$CONFIGS/.gitleaks.toml")" = "consumer-gitleaks-extends-baseline" ]
}

@test "markdownlint override applied" {
  echo "consumer-markdownlint" > "$WORKDIR/.markdownlint.local.yaml"
  cat > "$CONFIG_FILE" <<'YAML'
overrides:
  markdownlint: .markdownlint.local.yaml
YAML
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  [ "$(cat "$CONFIGS/.markdownlint-cli2.yaml")" = "consumer-markdownlint" ]
}

@test "missing override file: falls back to baseline" {
  cat > "$CONFIG_FILE" <<'YAML'
overrides:
  yamllint: nonexistent.yml
YAML
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  [ "$(cat "$CONFIGS/.yamllint")" = "baseline-yamllint" ]
}

@test "baseline preserved when override applied" {
  echo "consumer-yamllint" > "$WORKDIR/.yamllint.local.yml"
  cat > "$CONFIG_FILE" <<'YAML'
overrides:
  yamllint: .yamllint.local.yml
YAML
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  # Baseline file should be untouched
  [ "$(cat "$CONFIGS/.yamllint.baseline")" = "baseline-yamllint" ]
  # Active config should be the consumer's override
  [ "$(cat "$CONFIGS/.yamllint")" = "consumer-yamllint" ]
}

# ── Non-extends configs: full replacement ─────────────

@test "hadolint consumer override replaces default" {
  echo "custom-hadolint" > "$WORKDIR/.hadolint.yaml"
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  [ "$(cat "$CONFIGS/.hadolint.yaml")" = "custom-hadolint" ]
}

@test "jscpd consumer override replaces default" {
  echo "custom-jscpd" > "$WORKDIR/.jscpd.json"
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  [ "$(cat "$CONFIGS/.jscpd.json")" = "custom-jscpd" ]
}

# ── No hook copying ──────────────────────────────────

@test "does not copy hooks to workspace" {
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  # scripts/hooks/ should NOT exist in consumer workspace
  [ ! -d "$WORKDIR/scripts/hooks" ]
}

# ── Combined: skip-hooks + overrides ─────────────────

@test "skip-hooks and overrides both work together" {
  echo "consumer-yamllint" > "$WORKDIR/.yamllint.local.yml"
  cat > "$CONFIG_FILE" <<'YAML'
skip-hooks:
  - python
overrides:
  yamllint: .yamllint.local.yml
YAML
  run bash "$BATS_TEST_DIRNAME/../scripts/ci/apply-configs.sh"
  [ "$status" -eq 0 ]
  grep -q "skip-hooks=python" "$GITHUB_OUTPUT"
  [ "$(cat "$CONFIGS/.yamllint")" = "consumer-yamllint" ]
}
