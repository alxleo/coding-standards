"""Regression tests for custom MegaLinter descriptor command shapes."""

from pathlib import Path

import yaml


def test_dclint_receives_compose_files_without_removed_subcommand() -> None:
    descriptor = yaml.safe_load(Path("plugins/dclint.megalinter-descriptor.yml").read_text())
    dclint = descriptor["linters"][0]

    assert dclint["cli_lint_mode"] == "list_of_files"
    assert dclint["cli_lint_extra_args"] == []
