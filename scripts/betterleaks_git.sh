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

exec betterleaks "${args[@]}"
