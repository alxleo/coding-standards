"""Tests for entrypoint.py consumer rules-directory resolution."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


@pytest.fixture
def workspace(tmp_path):
    """Create a temp workspace with a baked config and consumer .mega-linter.yml."""
    # Baked config (minimal)
    baked = tmp_path / "baked.yml"
    baked.write_text(
        yaml.dump(
            {
                "ENABLE_LINTERS": "PYTHON_RUFF",
                "LINTER_RULES_PATH": "/opt/coding-standards/configs",
                "PYTHON_RUFF_CONFIG_FILE": "ruff.toml",
                "REPOSITORY_TRIVY_CUSTOM_CONFIG_FILE": "trivy.yaml",
            }
        )
    )

    # Patch constants
    with patch("scripts.entrypoint.BAKED_CONFIG", baked), patch("scripts.entrypoint._workspace", return_value=tmp_path):
        yield tmp_path


def _write_consumer_config(workspace: Path, overrides: dict) -> None:
    """Write a consumer .mega-linter.yml with EXTENDS + overrides."""
    from scripts.entrypoint import EXTENDS_URL  # noqa: PLC0415

    content = {"EXTENDS": [EXTENDS_URL]}
    content.update(overrides)
    (workspace / ".mega-linter.yml").write_text(yaml.dump(content))


def _run_setup():
    from scripts.entrypoint import _setup  # noqa: PLC0415

    _setup()


def _read_merged_config() -> dict:
    config_path = os.environ.get("MEGALINTER_CONFIG", "")
    assert config_path, "MEGALINTER_CONFIG not set after _setup()"
    return yaml.safe_load(Path(config_path).read_text())


class TestRulesDirectoryResolution:
    def test_rules_directory_applies_to_matching_linter(self, workspace):
        """A single rules directory selects a matching consumer config."""
        rules = workspace / "quality" / "lint"
        rules.mkdir(parents=True)
        (rules / "ruff.toml").write_text("[lint]\nselect = ['E']\n")
        (rules / "actionlint.yaml").write_text("self-hosted-runner: {}\n")
        (rules / "trivy.yaml").write_text("scan:\n  skip-dirs: [.decrypted]\n")
        _write_consumer_config(
            workspace,
            {
                "LINTER_RULES_PATH": "quality/lint",
                "ACTION_ACTIONLINT_CONFIG_FILE": "actionlint.yaml",
            },
        )

        _run_setup()

        merged = _read_merged_config()
        assert "PYTHON_RUFF_RULES_PATH" not in merged
        assert merged["PYTHON_RUFF_CONFIG_FILE"] == "quality/lint/ruff.toml"
        assert "ACTION_ACTIONLINT_RULES_PATH" not in merged
        assert merged["ACTION_ACTIONLINT_CONFIG_FILE"] == "quality/lint/actionlint.yaml"
        assert merged["REPOSITORY_TRIVY_CUSTOM_CONFIG_FILE"] == "quality/lint/trivy.yaml"

    def test_rules_directory_preserves_baked_fallback(self, workspace):
        """Linters without a consumer config retain the baked rules path."""
        baked = workspace / "baked.yml"
        baked.write_text(
            yaml.dump(
                {
                    "LINTER_RULES_PATH": "/opt/coding-standards/configs",
                    "PYTHON_RUFF_CONFIG_FILE": "ruff.toml",
                }
            )
        )
        rules = workspace / "quality" / "lint"
        rules.mkdir(parents=True)
        _write_consumer_config(workspace, {"LINTER_RULES_PATH": "quality/lint"})

        _run_setup()

        merged = _read_merged_config()
        assert merged["LINTER_RULES_PATH"] == "/opt/coding-standards/configs"
        assert "PYTHON_RUFF_RULES_PATH" not in merged

    def test_explicit_missing_file_produces_warning(self, workspace, capsys):
        """Missing file within workspace produces a stderr warning."""
        rules = workspace / "quality" / "lint"
        rules.mkdir(parents=True)
        _write_consumer_config(
            workspace,
            {"LINTER_RULES_PATH": "quality/lint", "PYTHON_RUFF_CONFIG_FILE": "nonexistent.toml"},
        )

        _run_setup()

        merged = _read_merged_config()
        assert merged["PYTHON_RUFF_CONFIG_FILE"] == "nonexistent.toml"

        captured = capsys.readouterr()
        assert "Warning: PYTHON_RUFF_CONFIG_FILE override points to missing file" in captured.err

    def test_invalid_rules_directory_rejected(self, workspace):
        _write_consumer_config(workspace, {"LINTER_RULES_PATH": "../../outside"})

        with pytest.raises(ValueError, match="workspace directory"):
            _run_setup()

    def test_explicit_per_linter_rules_path_wins(self, workspace):
        rules = workspace / "quality" / "lint"
        rules.mkdir(parents=True)
        (rules / "ruff.toml").write_text("[lint]\n")
        _write_consumer_config(
            workspace,
            {"LINTER_RULES_PATH": "quality/lint", "PYTHON_RUFF_RULES_PATH": "custom/ruff"},
        )

        _run_setup()

        merged = _read_merged_config()
        assert merged["PYTHON_RUFF_RULES_PATH"] == "custom/ruff"
        assert merged["PYTHON_RUFF_CONFIG_FILE"] == "ruff.toml"

    def test_required_local_configs_resolve_and_private_key_is_removed(self, workspace):
        rules = workspace / "quality" / "lint"
        rules.mkdir(parents=True)
        (rules / "ruff.toml").write_text("[lint]\n")
        _write_consumer_config(
            workspace,
            {
                "LINTER_RULES_PATH": "quality/lint",
                "CODING_STANDARDS_REQUIRED_LOCAL_CONFIGS": ["PYTHON_RUFF_CONFIG_FILE"],
            },
        )

        _run_setup()

        merged = _read_merged_config()
        assert merged["PYTHON_RUFF_CONFIG_FILE"] == "quality/lint/ruff.toml"
        assert "CODING_STANDARDS_REQUIRED_LOCAL_CONFIGS" not in merged

    def test_required_local_config_missing_fails_closed(self, workspace):
        (workspace / "quality" / "lint").mkdir(parents=True)
        _write_consumer_config(
            workspace,
            {
                "LINTER_RULES_PATH": "quality/lint",
                "CODING_STANDARDS_REQUIRED_LOCAL_CONFIGS": ["PYTHON_RUFF_CONFIG_FILE"],
            },
        )

        with pytest.raises(ValueError, match="PYTHON_RUFF_CONFIG_FILE"):
            _run_setup()

    def test_required_local_config_rejects_root_override(self, workspace):
        (workspace / "quality" / "lint").mkdir(parents=True)
        (workspace / "ruff.toml").write_text("[lint]\n")
        _write_consumer_config(
            workspace,
            {
                "LINTER_RULES_PATH": "quality/lint",
                "PYTHON_RUFF_CONFIG_FILE": "ruff.toml",
                "CODING_STANDARDS_REQUIRED_LOCAL_CONFIGS": ["PYTHON_RUFF_CONFIG_FILE"],
            },
        )

        with pytest.raises(ValueError, match="not a file under quality/lint"):
            _run_setup()
