"""Tests for show_config.py.

Uses tmp_path fixtures to simulate workspace dirs with/without shadowing configs.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Import via spec loader (script lives in scripts/, not a package)
_script = Path(__file__).resolve().parent.parent / "scripts" / "show_config.py"
_spec = importlib.util.spec_from_file_location("show_config", _script)
assert _spec is not None, f"Could not load spec from {_script}"
_mod = importlib.util.module_from_spec(_spec)
sys.modules["show_config"] = _mod
assert _spec.loader is not None, "spec has no loader"
_spec.loader.exec_module(_mod)

show_config = _mod.show_config
main = _mod.main
_extract_config_entries = _mod._extract_config_entries
_find_shadows = _mod._find_shadows


@pytest.fixture()
def sample_yml(tmp_path: Path) -> Path:
    """Minimal .mega-linter-default.yml with a few _CONFIG_FILE entries."""
    content = """\
ENABLE_LINTERS:
  - PYTHON_RUFF
  - BASH_SHELLCHECK
  - YAML_YAMLLINT

DISABLE_ERRORS_LINTERS:
  - YAML_YAMLLINT

PYTHON_RUFF_CONFIG_FILE: /opt/coding-standards/configs/ruff.toml
BASH_SHELLCHECK_CONFIG_FILE: /opt/coding-standards/configs/.shellcheckrc
YAML_YAMLLINT_CONFIG_FILE: /opt/coding-standards/configs/.yamllint
"""
    yml = tmp_path / ".mega-linter-default.yml"
    yml.write_text(content)
    return yml


@pytest.fixture()
def empty_workspace(tmp_path: Path) -> Path:
    """Workspace with no local config files."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture()
def workspace_with_ruff(tmp_path: Path) -> Path:
    """Workspace that has a local ruff.toml (shadows baked config)."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "ruff.toml").write_text("[lint]\nselect = []\n")
    return ws


class TestExtractConfigEntries:
    def test_extracts_config_file_keys(self, sample_yml: Path) -> None:
        entries = _extract_config_entries(sample_yml)
        linters = [e["linter"] for e in entries]
        assert "PYTHON_RUFF" in linters
        assert "BASH_SHELLCHECK" in linters
        assert "YAML_YAMLLINT" in linters

    def test_extracts_basenames(self, sample_yml: Path) -> None:
        entries = _extract_config_entries(sample_yml)
        basenames = {e["linter"]: e["config_basename"] for e in entries}
        assert basenames["PYTHON_RUFF"] == "ruff.toml"
        assert basenames["BASH_SHELLCHECK"] == ".shellcheckrc"

    def test_ignores_non_config_keys(self, sample_yml: Path) -> None:
        entries = _extract_config_entries(sample_yml)
        # ENABLE_LINTERS and DISABLE_ERRORS_LINTERS should NOT appear
        linters = [e["linter"] for e in entries]
        assert "ENABLE_LINTERS" not in linters


class TestFindShadows:
    def test_no_shadows_in_empty_workspace(self, empty_workspace: Path) -> None:
        assert _find_shadows(empty_workspace, "ruff.toml") == []

    def test_finds_exact_match(self, workspace_with_ruff: Path) -> None:
        shadows = _find_shadows(workspace_with_ruff, "ruff.toml")
        assert "ruff.toml" in shadows

    def test_finds_pyproject_as_ruff_shadow(self, workspace_with_ruff: Path) -> None:
        (workspace_with_ruff / "pyproject.toml").write_text("[tool.ruff]\n")
        shadows = _find_shadows(workspace_with_ruff, "ruff.toml")
        assert "ruff.toml" in shadows
        assert "pyproject.toml" in shadows

    def test_unknown_config_falls_back_to_basename(self, tmp_path: Path) -> None:
        """Configs not in _SHADOW_NAMES should check for exact basename match."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / "unknown.cfg").write_text("")
        assert _find_shadows(ws, "unknown.cfg") == ["unknown.cfg"]


class TestShowConfig:
    def test_no_shadows_in_empty_workspace(
        self, empty_workspace: Path, sample_yml: Path
    ) -> None:
        rows = show_config(empty_workspace, sample_yml)
        assert len(rows) == 3
        assert all(r["shadow"] == "" for r in rows)

    def test_detects_shadow(
        self, workspace_with_ruff: Path, sample_yml: Path
    ) -> None:
        rows = show_config(workspace_with_ruff, sample_yml)
        ruff_row = next(r for r in rows if r["linter"] == "PYTHON_RUFF")
        assert "ruff.toml" in ruff_row["shadow"]

    def test_tier_classification(
        self, empty_workspace: Path, sample_yml: Path
    ) -> None:
        rows = show_config(empty_workspace, sample_yml)
        tiers = {r["linter"]: r["tier"] for r in rows}
        assert tiers["PYTHON_RUFF"] == "error"
        assert tiers["YAML_YAMLLINT"] == "warn"
        assert tiers["BASH_SHELLCHECK"] == "error"


class TestMain:
    def test_missing_yml_returns_1(self, tmp_path: Path) -> None:
        result = main([".", "--mega-linter-yml", str(tmp_path / "nonexistent.yml")])
        assert result == 1

    def test_valid_run_returns_0(
        self, empty_workspace: Path, sample_yml: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        result = main([str(empty_workspace), "--mega-linter-yml", str(sample_yml)])
        assert result == 0
        captured = capsys.readouterr()
        assert "PYTHON_RUFF" in captured.out
        assert "ruff.toml" in captured.out

    def test_output_table_has_header(
        self, empty_workspace: Path, sample_yml: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main([str(empty_workspace), "--mega-linter-yml", str(sample_yml)])
        captured = capsys.readouterr()
        assert "Linter" in captured.out
        assert "Config" in captured.out
        assert "Tier" in captured.out
        assert "Local Override" in captured.out

    def test_shadow_count_in_summary(
        self, workspace_with_ruff: Path, sample_yml: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main([str(workspace_with_ruff), "--mega-linter-yml", str(sample_yml)])
        captured = capsys.readouterr()
        assert "3 linters with baked configs" in captured.out
        assert "1 overridden locally" in captured.out
