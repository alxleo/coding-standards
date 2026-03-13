#!/usr/bin/env bats
# Validates the format of scripts/ci/groups.conf

GROUPS_CONF="scripts/ci/groups.conf"

@test "groups.conf exists" {
  [ -f "$GROUPS_CONF" ]
}

@test "every non-comment line has exactly 4 pipe-delimited fields" {
  while IFS= read -r line; do
    [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
    field_count=$(echo "$line" | awk -F'|' '{print NF}')
    if [ "$field_count" -ne 4 ]; then
      echo "Bad line (${field_count} fields): $line"
      return 1
    fi
  done < "$GROUPS_CONF"
}

@test "no empty fields in any line" {
  while IFS='|' read -r logkey display_name status_context step_name; do
    [[ "$logkey" =~ ^#.*$ || -z "$logkey" ]] && continue
    if [ -z "$display_name" ] || [ -z "$status_context" ] || [ -z "$step_name" ]; then
      echo "Empty field in: $logkey|$display_name|$status_context|$step_name"
      return 1
    fi
  done < "$GROUPS_CONF"
}

@test "logkeys are unique" {
  local keys
  keys=$(grep -v '^#' "$GROUPS_CONF" | grep -v '^$' | cut -d'|' -f1 | sort)
  local unique_keys
  unique_keys=$(echo "$keys" | uniq)
  if [ "$keys" != "$unique_keys" ]; then
    echo "Duplicate logkeys found:"
    echo "$keys" | uniq -d
    return 1
  fi
}

@test "logkeys are alphanumeric with hyphens only" {
  while IFS='|' read -r logkey rest; do
    [[ "$logkey" =~ ^#.*$ || -z "$logkey" ]] && continue
    if ! [[ "$logkey" =~ ^[a-z0-9-]+$ ]]; then
      echo "Invalid logkey: $logkey"
      return 1
    fi
  done < "$GROUPS_CONF"
}

@test "step_names match a lint.yml step" {
  local lint_yml=".github/workflows/lint.yml"
  [ -f "$lint_yml" ] || skip "lint.yml not found"
  while IFS='|' read -r logkey display_name status_context step_name; do
    [[ "$logkey" =~ ^#.*$ || -z "$logkey" ]] && continue
    if ! grep -qF "\"$step_name\"" "$lint_yml" && ! grep -qF "'$step_name'" "$lint_yml"; then
      # Check without quotes too (YAML allows unquoted)
      if ! grep -qF "name: $step_name" "$lint_yml"; then
        echo "Step name not found in lint.yml: $step_name"
        return 1
      fi
    fi
  done < "$GROUPS_CONF"
}
