"""Regression tests for custom MegaLinter descriptor command shapes."""

from pathlib import Path

import yaml


def test_dclint_receives_compose_files_without_removed_subcommand() -> None:
    descriptor = yaml.safe_load(Path("plugins/dclint.megalinter-descriptor.yml").read_text())
    dclint = descriptor["linters"][0]

    assert dclint["cli_lint_mode"] == "list_of_files"
    assert dclint["cli_lint_extra_args"] == []
    assert dclint["cli_config_arg_name"] == "--config"
    assert dclint["config_file_name"] == ".dclintrc.yaml"


def test_betterleaks_scans_git_history_with_compatible_config() -> None:
    descriptor = yaml.safe_load(Path("plugins/betterleaks-git.megalinter-descriptor.yml").read_text())
    betterleaks = descriptor["linters"][0]

    assert betterleaks["name"] == "REPOSITORY_BETTERLEAKS_GIT"
    assert betterleaks["cli_lint_mode"] == "project"
    assert betterleaks["cli_lint_extra_args"][0] == "git"
    assert betterleaks["config_file_name"] == ".gitleaks.toml"
    assert betterleaks["cli_lint_extra_args_after"] == ["."]

    wrapper = Path("scripts/betterleaks_git.sh").read_text()
    assert "GIT_CONFIG_KEY_${git_config_index}=safe.directory" in wrapper
    assert "GIT_CONFIG_VALUE_${git_config_index}=$(pwd -P)" in wrapper
