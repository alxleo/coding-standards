"""Tests for entrypoint.py consumer config resolution."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

SEMGREP_ARGUMENTS = "REPOSITORY_SEMGREP_ARGUMENTS"
SHARED_ARGUMENTS = ["--exclude=semgrep-rules", "--exclude-rule=rules.trailofbits.shared-rule"]
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / ".mega-linter-default.yml"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Create a temp workspace with a baked config and consumer .mega-linter.yml."""
    # Baked config (minimal)
    baked = tmp_path / "baked.yml"
    baked.write_text(
        yaml.dump(
            {
                "ENABLE_LINTERS": "PYTHON_RUFF",
                "LINTER_RULES_PATH": "/opt/coding-standards/configs",
                "PYTHON_RUFF_CONFIG_FILE": "ruff.toml",
                SEMGREP_ARGUMENTS: SHARED_ARGUMENTS,
            }
        )
    )

    monkeypatch.delenv("MEGALINTER_CONFIG", raising=False)
    monkeypatch.delenv(SEMGREP_ARGUMENTS, raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.delenv("ENABLE_LINTERS", raising=False)
    monkeypatch.delenv("DISABLE_LINTERS", raising=False)
    monkeypatch.delenv("ENABLE_DISABLE_LINTERS_PRIORITY", raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setattr("scripts.entrypoint.tempfile.tempdir", tmp_path)

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


def test_consumer_enable_list_cannot_reactivate_trivy(workspace):
    with patch("scripts.entrypoint.BAKED_CONFIG", DEFAULT_CONFIG):
        _write_consumer_config(
            workspace,
            {"ENABLE_LINTERS": ["REPOSITORY_TRIVY", "REPOSITORY_TRIVY_CUSTOM"]},
        )

        _run_setup()
        merged = _read_merged_config()

    assert set(merged["ENABLE_LINTERS"]) == {"REPOSITORY_TRIVY", "REPOSITORY_TRIVY_CUSTOM"}
    assert set(merged["DISABLE_LINTERS"]) == {
        "REPOSITORY_TRIVY",
        "REPOSITORY_TRIVY_CUSTOM",
        "REPOSITORY_TRIVY_SBOM",
    }
    assert merged["ENABLE_DISABLE_LINTERS_PRIORITY"] == "DISABLE"


@pytest.mark.parametrize("event", ["pull_request", "pull_request_target", "schedule"])
@pytest.mark.parametrize("environment_override", [False, True])
def test_legacy_consumer_scanner_policy(workspace, monkeypatch, event, environment_override):
    _write_consumer_config(
        workspace,
        {
            "ENABLE_LINTERS": ["REPOSITORY_TRIVY", "REPOSITORY_SEMGREP", "PYTHON_RUFF", "YAML_YAMLLINT"],
            "DISABLE_LINTERS": ["YAML_YAMLLINT"],
        },
    )
    monkeypatch.setenv("GITHUB_EVENT_NAME", event)
    if environment_override:
        monkeypatch.setenv("DISABLE_LINTERS", "PYTHON_RUFF")

    _run_setup()

    disabled = set(os.environ["DISABLE_LINTERS"].split(","))
    assert {"REPOSITORY_TRIVY", "REPOSITORY_TRIVY_CUSTOM", "REPOSITORY_TRIVY_SBOM"} <= disabled
    assert ("REPOSITORY_SEMGREP" in disabled) == event.startswith("pull_request")
    assert ("YAML_YAMLLINT" in disabled) is not environment_override
    assert ("PYTHON_RUFF" in disabled) is environment_override
    assert os.environ["ENABLE_DISABLE_LINTERS_PRIORITY"] == "DISABLE"


def test_setup_continues_after_git_config_timeout(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("MEGALINTER_CONFIG", "")
    with patch("scripts.entrypoint.subprocess.run", side_effect=subprocess.TimeoutExpired("git config", 10)):
        _run_setup()

    assert os.environ["MEGALINTER_CONFIG"] == str(workspace / "baked.yml")
    assert "git config timed out" in capsys.readouterr().err


@pytest.mark.parametrize(
    "local", ["--jobs 2 --exclude='folder with spaces'", ["--jobs", "2", "--exclude=folder with spaces"]]
)
def test_shared_semgrep_exclusions_survive_yaml_arguments(workspace, local):
    _write_consumer_config(workspace, {SEMGREP_ARGUMENTS: local})

    _run_setup()

    assert _read_merged_config()[SEMGREP_ARGUMENTS] == [
        *SHARED_ARGUMENTS,
        "--jobs",
        "2",
        "--exclude=folder with spaces",
    ]


@pytest.mark.parametrize("extends_baseline", [False, True])
def test_shared_semgrep_exclusions_survive_environment_arguments(workspace, monkeypatch, extends_baseline):
    if extends_baseline:
        _write_consumer_config(workspace, {SEMGREP_ARGUMENTS: ["--jobs", "8"]})
    monkeypatch.setenv(SEMGREP_ARGUMENTS, "--jobs 2 --exclude=semgrep-rules --exclude='folder with spaces'")

    _run_setup()

    assert shlex.split(os.environ[SEMGREP_ARGUMENTS]) == [
        SHARED_ARGUMENTS[1],
        "--jobs",
        "2",
        "--exclude=semgrep-rules",
        "--exclude=folder with spaces",
    ]


def test_blank_semgrep_override_keeps_shared_exclusions(workspace, monkeypatch):
    _write_consumer_config(workspace, {SEMGREP_ARGUMENTS: None})
    monkeypatch.setenv(SEMGREP_ARGUMENTS, "")

    _run_setup()

    assert _read_merged_config()[SEMGREP_ARGUMENTS] == SHARED_ARGUMENTS
    assert shlex.split(os.environ[SEMGREP_ARGUMENTS]) == SHARED_ARGUMENTS


def test_shared_semgrep_exclusion_uses_original_id_when_rewriting_disabled(workspace):
    _write_consumer_config(workspace, {SEMGREP_ARGUMENTS: ["--no-rewrite-rule-ids"]})

    _run_setup()

    assert _read_merged_config()[SEMGREP_ARGUMENTS] == [
        "--exclude=semgrep-rules",
        "--exclude-rule=trailofbits.shared-rule",
        "--no-rewrite-rule-ids",
    ]


def test_standalone_semgrep_config_keeps_its_own_arguments(workspace, monkeypatch):
    (workspace / ".mega-linter.yml").write_text(yaml.safe_dump({SEMGREP_ARGUMENTS: ["--jobs", "8"]}))
    monkeypatch.setenv(SEMGREP_ARGUMENTS, "--jobs 2")

    _run_setup()

    assert "MEGALINTER_CONFIG" not in os.environ
    assert os.environ[SEMGREP_ARGUMENTS] == "--jobs 2"


class TestRulesDirectoryResolution:
    def test_rules_directory_applies_to_matching_linter(self, workspace):
        """A single rules directory selects a matching consumer config."""
        rules = workspace / "quality" / "lint"
        rules.mkdir(parents=True)
        (rules / "ruff.toml").write_text("[lint]\nselect = ['E']\n")
        (rules / "actionlint.yaml").write_text("self-hosted-runner: {}\n")
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

    @pytest.mark.parametrize("rules_path", ["/opt/custom", "https://example.com/configs"])
    def test_required_local_configs_reject_non_local_rules_path(self, workspace, rules_path):
        _write_consumer_config(
            workspace,
            {
                "LINTER_RULES_PATH": rules_path,
                "CODING_STANDARDS_REQUIRED_LOCAL_CONFIGS": ["PYTHON_RUFF_CONFIG_FILE"],
            },
        )

        with pytest.raises(ValueError, match="workspace-relative LINTER_RULES_PATH"):
            _run_setup()
