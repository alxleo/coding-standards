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

  # Find entry paths for language: system hooks.
  # Look for entry: lines within system-language hook blocks.
  local rc=0
  local in_system=0
  while IFS= read -r line; do
    # Track when we enter a language: system block
    if echo "$line" | grep -qE '^\s+language:\s+system'; then
      in_system=1
      continue
    fi
    # New hook block resets the flag
    if echo "$line" | grep -qE '^\s+- id:'; then
      in_system=0
      continue
    fi
    # New repo block resets the flag
    if echo "$line" | grep -qE '^- repo:'; then
      in_system=0
      continue
    fi
    # Check entry lines in system blocks
    if [ "$in_system" -eq 1 ] && echo "$line" | grep -qE '^\s+entry:'; then
      local entry
      entry=$(echo "$line" | sed 's/.*entry:\s*//' | sed 's/^\s*//' | sed "s/^['\"]//;s/['\"]$//" | awk '{print $1}')

      # Skip inline commands (just, bash, etc.)
      case "$entry" in
        just|bash|sh|python*|node|ruby) continue ;;
      esac

      # Strip .coding-standards/ prefix for repo-local check
      local path="$entry"
      path="${path#.coding-standards/}"

      if [ ! -f "$path" ]; then
        echo "MISSING: hook entry '$entry' → file not found at '$path'"
        rc=1
      fi
    fi
  done < "$PRE_COMMIT"
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
