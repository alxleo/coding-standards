#!/usr/bin/env bash
set -euo pipefail

args=("$@")
config_file=""
has_ignore_path=false

for ((index = 0; index < ${#args[@]}; index++)); do
  case "${args[index]}" in
    -c | --config)
      if ((index + 1 < ${#args[@]})); then
        config_file="${args[index + 1]}"
      fi
      ;;
    --config=*)
      config_file="${args[index]#*=}"
      ;;
    -i | --gitleaks-ignore-path | --gitleaks-ignore-path=*)
      has_ignore_path=true
      ;;
  esac
done

if [[ -n "$config_file" && "$has_ignore_path" == false ]]; then
  ignore_file="$(dirname -- "$config_file")/.gitleaksignore"
  if [[ -f "$ignore_file" ]]; then
    args+=(--gitleaks-ignore-path "$ignore_file")
  fi
fi

# Betterleaks shells out to Git but does not reliably consume MegaLinter's
# global safe.directory setting on runner-owned bind mounts. Pass the workspace
# as command-scope Git configuration inherited by the child process.
git_config_index="${GIT_CONFIG_COUNT:-0}"
export "GIT_CONFIG_KEY_${git_config_index}=safe.directory"
export "GIT_CONFIG_VALUE_${git_config_index}=$(pwd -P)"
export GIT_CONFIG_COUNT="$((git_config_index + 1))"

exec betterleaks "${args[@]}"
