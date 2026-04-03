"""Tests for entrypoint.py _CONFIG_FILE path resolution logic."""

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
    baked.write_text(yaml.dump({"ENABLE_LINTERS": "PYTHON_RUFF"}))

    # Patch constants
    with patch("scripts.entrypoint.BAKED_CONFIG", baked), patch("scripts.entrypoint._workspace", return_value=tmp_path):
        yield tmp_path


def _write_consumer_config(workspace: Path, overrides: dict) -> None:
    """Write a consumer .mega-linter.yml with EXTENDS + overrides."""
    from scripts.entrypoint import EXTENDS_URL

    content = {"EXTENDS": [EXTENDS_URL]}
    content.update(overrides)
    (workspace / ".mega-linter.yml").write_text(yaml.dump(content))


def _run_setup():
    from scripts.entrypoint import _setup

    _setup()


def _read_merged_config() -> dict:
    config_path = os.environ.get("MEGALINTER_CONFIG", "")
    assert config_path, "MEGALINTER_CONFIG not set after _setup()"
    return yaml.safe_load(Path(config_path).read_text())


class TestConfigFileResolution:
    def test_relative_config_rewritten_to_absolute(self, workspace):
        """Consumer ruff.toml override is rewritten to workspace-absolute path."""
        (workspace / "ruff.toml").write_text("[lint]\nselect = ['E']\n")
        _write_consumer_config(workspace, {"PYTHON_RUFF_CONFIG_FILE": "ruff.toml"})

        _run_setup()

        merged = _read_merged_config()
        expected = str((workspace / "ruff.toml").resolve())
        assert merged["PYTHON_RUFF_CONFIG_FILE"] == expected

    def test_path_traversal_rejected(self, workspace):
        """../../etc/passwd traversal is blocked by is_relative_to check."""
        _write_consumer_config(workspace, {"PYTHON_RUFF_CONFIG_FILE": "../../etc/passwd"})

        _run_setup()

        merged = _read_merged_config()
        # Should NOT be rewritten — the original relative path stays as-is
        assert merged.get("PYTHON_RUFF_CONFIG_FILE") == "../../etc/passwd"

    def test_missing_file_produces_warning(self, workspace, capsys):
        """Missing file within workspace produces a stderr warning."""
        _write_consumer_config(workspace, {"PYTHON_RUFF_CONFIG_FILE": "nonexistent.toml"})

        _run_setup()

        merged = _read_merged_config()
        # Not rewritten since file doesn't exist
        assert merged.get("PYTHON_RUFF_CONFIG_FILE") != str(workspace / "nonexistent.toml")

        captured = capsys.readouterr()
        assert "Warning: PYTHON_RUFF_CONFIG_FILE override points to missing file" in captured.err

    def test_absolute_path_not_modified(self, workspace):
        """Absolute paths are left as-is (consumer knows what they're doing)."""
        _write_consumer_config(workspace, {"PYTHON_RUFF_CONFIG_FILE": "/opt/custom/ruff.toml"})

        _run_setup()

        merged = _read_merged_config()
        assert merged["PYTHON_RUFF_CONFIG_FILE"] == "/opt/custom/ruff.toml"

    def test_non_config_file_keys_not_modified(self, workspace):
        """Keys that don't end in _CONFIG_FILE are left alone."""
        _write_consumer_config(workspace, {"PYTHON_RUFF_ARGUMENTS": ["--fix"]})

        _run_setup()

        merged = _read_merged_config()
        assert merged["PYTHON_RUFF_ARGUMENTS"] == ["--fix"]
