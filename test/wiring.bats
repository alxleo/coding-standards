#!/usr/bin/env bats
# Wiring validation — ensures all linter groups are properly connected.
# Catches orphaned steps, missing hook scripts, and stale documentation.

GROUPS_CONF="scripts/ci/groups.conf"
LINT_YML=".github/workflows/lint.yml"
PRE_COMMIT="lint-configs-626465/.pre-commit-config.yaml"
EXAMPLES="examples/.coding-standards.yml"

# ── Reverse validation: lint.yml → groups.conf ────────

@test "every lint-run.sh logkey in lint.yml has a groups.conf entry" {
  # Extract logkeys from lint.yml (first arg after /tmp/lint-run.sh)
  local yml_keys
  yml_keys=$(grep -oE '/tmp/lint-run\.sh [a-z0-9-]+' "$LINT_YML" | awk '{print $2}' | sort -u)

  # Extract logkeys from groups.conf
  local conf_keys
  conf_keys=$(grep -v '^#' "$GROUPS_CONF" | grep -v '^$' | cut -d'|' -f1 | sort)

  for key in $yml_keys; do
    if ! echo "$conf_keys" | grep -qx "$key"; then
      echo "ORPHAN: lint.yml has step with logkey '$key' but no groups.conf entry"
      echo "  → This step will not report a commit status"
      return 1
    fi
  done
}

# ── Hook script existence ─────────────────────────────

@test "all language:system hook scripts exist" {
  [ -f "$PRE_COMMIT" ] || skip "pre-commit config not found"

  # Collect entry + language per hook block, validate at block boundaries.
  # Fields can appear in any order within a block.
  local rc=0
  local cur_entry="" cur_is_system=0
  validate_block() {
    if [ "$cur_is_system" -eq 1 ] && [ -n "$cur_entry" ]; then
      # Skip inline commands (not file paths)
      case "$cur_entry" in
        just|bash|sh|python*|node|ruby|prettier|eslint|tflint|knip|madge|trivy|semgrep|license-checker) return ;;
      esac
      local path="$cur_entry"
      path="${path#.coding-standards/}"
      if [ ! -f "$path" ]; then
        echo "MISSING: hook entry '$cur_entry' → file not found at '$path'"
        rc=1
      fi
    fi
    cur_entry=""
    cur_is_system=0
  }

  while IFS= read -r line; do
    # New hook or repo block — validate previous, reset
    if echo "$line" | grep -qE '^\s+- id:|^- repo:'; then
      validate_block
      continue
    fi
    if echo "$line" | grep -qE '^\s+language:\s+system'; then
      cur_is_system=1
      continue
    fi
    if echo "$line" | grep -qE '^\s+entry:'; then
      cur_entry=$(echo "$line" | sed "s/.*entry:[ ]*//" | sed "s/^[ '\"]*//;s/['\"]$//" | awk '{print $1}')
      continue
    fi
  done < "$PRE_COMMIT"
  # Validate final block
  validate_block
  [ "$rc" -eq 0 ]
}

# ── Examples group list sync ──────────────────────────

@test "examples/.coding-standards.yml lists all groups from groups.conf" {
  [ -f "$EXAMPLES" ] || skip "examples file not found"

  # Extract all logkeys from groups.conf (except 'extra' which is special)
  local conf_keys
  conf_keys=$(grep -v '^#' "$GROUPS_CONF" | grep -v '^$' | cut -d'|' -f1 | grep -v '^extra$')

  # Extract group names mentioned in the Available groups comment block
  local example_groups
  example_groups=$(grep -A 10 'Available groups:' "$EXAMPLES" | grep '^#' | tr ',' '\n' | sed 's/[# ]//g' | grep -v '^$' | sort)

  local rc=0
  for key in $conf_keys; do
    if ! echo "$example_groups" | grep -qx "$key"; then
      echo "MISSING: group '$key' is in groups.conf but not in examples/.coding-standards.yml"
      rc=1
    fi
  done
  [ "$rc" -eq 0 ]
}
