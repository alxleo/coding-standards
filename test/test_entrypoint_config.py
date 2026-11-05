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


class TestConsumerConfigDiscovery:
    @pytest.fixture(autouse=True)
    def _fresh_env(self, monkeypatch):
        monkeypatch.delenv("MEGALINTER_CONFIG", raising=False)

    def _merged_or_none(self) -> dict | None:
        config_path = os.environ.get("MEGALINTER_CONFIG")
        return yaml.safe_load(Path(config_path).read_text()) if config_path else None

    @pytest.mark.parametrize("name", [".megalinter.yml", ".mega-linter.yaml", ".config/mega-linter.yml"])
    def test_other_megalinter_filenames_extend_the_baseline(self, workspace, name):
        from scripts.entrypoint import EXTENDS_URL  # noqa: PLC0415

        path = workspace / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump({"EXTENDS": [EXTENDS_URL], "DISABLE_LINTERS": ["SQL_SQLFLUFF"]}))

        _run_setup()

        merged = self._merged_or_none()
        assert merged is not None, "consumer config under another name was ignored"
        assert merged["DISABLE_LINTERS"] == ["SQL_SQLFLUFF"]
        assert merged["ENABLE_LINTERS"] == "PYTHON_RUFF"

    def test_standalone_config_under_another_name_is_not_replaced_by_the_baseline(self, workspace):
        (workspace / ".megalinter.yml").write_text(yaml.dump({"ENABLE_LINTERS": ["BASH_SHELLCHECK"]}))

        _run_setup()

        assert "MEGALINTER_CONFIG" not in os.environ

    def test_config_without_extends_stands_alone(self, workspace):
        (workspace / ".mega-linter.yml").write_text(yaml.dump({"ENABLE_LINTERS": ["BASH_SHELLCHECK"]}))

        _run_setup()

        assert "MEGALINTER_CONFIG" not in os.environ

    @pytest.mark.parametrize(
        "extends_yaml",
        [
            'EXTENDS:\n  - "{url}"\n',
            "EXTENDS: {url}\n",
            "EXTENDS: [{url}]\n",
        ],
    )
    def test_any_yaml_form_of_the_baseline_extends_is_merged_offline(self, workspace, extends_yaml):
        from scripts.entrypoint import EXTENDS_URL  # noqa: PLC0415

        text = extends_yaml.format(url=EXTENDS_URL) + "DISABLE_LINTERS: [SQL_SQLFLUFF]\n"
        (workspace / ".mega-linter.yml").write_text(text)

        _run_setup()

        merged = self._merged_or_none()
        assert merged is not None
        assert "EXTENDS" not in merged, "baseline EXTENDS would make MegaLinter fetch it at runtime"
        assert merged["DISABLE_LINTERS"] == ["SQL_SQLFLUFF"]

    def test_other_extends_entries_are_kept(self, workspace):
        from scripts.entrypoint import EXTENDS_URL  # noqa: PLC0415

        own = "https://example.com/team-overrides.yml"
        config = f"EXTENDS:\n  - {EXTENDS_URL}\n  - {own}\nSHOW_ELAPSED_TIME: true\n"
        (workspace / ".mega-linter.yml").write_text(config)

        _run_setup()

        merged = self._merged_or_none()
        assert merged["EXTENDS"] == [own]
        assert merged["SHOW_ELAPSED_TIME"] is True


class TestLinterNameResolution:
    @pytest.fixture(autouse=True)
    def _baked_linters(self, tmp_path, monkeypatch):
        baked = tmp_path / "linters.yml"
        linters = ["PYTHON_RUFF", "PYTHON_RUFF_FORMAT", "BASH_SHELLCHECK", "REPOSITORY_SEMGREP"]
        baked.write_text(yaml.dump({"ENABLE_LINTERS": linters}))
        monkeypatch.setenv("MEGALINTER_CONFIG", str(baked))

    def _resolve(self, name: str) -> str:
        from scripts.entrypoint import _resolve_linters  # noqa: PLC0415

        return _resolve_linters(name)

    @pytest.mark.parametrize(
        ("requested", "expected"),
        [
            ("ruff", "PYTHON_RUFF"),
            ("ruff_format", "PYTHON_RUFF_FORMAT"),
            ("PYTHON_RUFF", "PYTHON_RUFF"),
            ("shellcheck,semgrep", "BASH_SHELLCHECK,REPOSITORY_SEMGREP"),
            ("PYTHON_BLACK", "PYTHON_BLACK"),
        ],
    )
    def test_short_and_full_names(self, requested, expected):
        assert self._resolve(requested) == expected

    def test_unknown_short_name_fails_instead_of_running_nothing(self):
        import typer  # noqa: PLC0415

        with pytest.raises(typer.Exit) as exc:
            self._resolve("rufff")
        assert exc.value.exit_code == 2
