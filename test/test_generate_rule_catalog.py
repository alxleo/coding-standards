"""Tests for generate_rule_catalog.py.

Covers the extractors that caused build failures:
- ruff status field format (string vs dict)
- normalize_severity argument count
- semgrep YAML parsing
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest
from pydantic import ValidationError

# Import via spec loader (script lives in scripts/, not a package)
_script = Path(__file__).resolve().parent.parent / "scripts" / "generate_rule_catalog.py"
_spec = importlib.util.spec_from_file_location("generate_rule_catalog", _script)
assert _spec is not None
_mod = importlib.util.module_from_spec(_spec)
sys.modules["generate_rule_catalog"] = _mod
assert _spec.loader is not None
with patch.object(sys, "path", [str(_script.parent), *sys.path]):
    _spec.loader.exec_module(_mod)

_normalize_severity = _mod._normalize_severity
extract_semgrep = _mod.extract_semgrep


# ── _normalize_severity ──────────────────────────────────────


class TestNormalizeSeverity:
    def test_standard_mappings(self) -> None:
        assert _normalize_severity("error") == "error"
        assert _normalize_severity("WARNING") == "warning"
        assert _normalize_severity("info") == "info"
        assert _normalize_severity("ignore") == "ignore"

    def test_aliases(self) -> None:
        assert _normalize_severity("deny") == "error"
        assert _normalize_severity("warn") == "warning"
        assert _normalize_severity("style") == "info"
        assert _normalize_severity("fatal") == "error"

    def test_unknown_defaults_to_warning(self) -> None:
        assert _normalize_severity("unknown") == "warning"

    def test_takes_one_argument(self) -> None:
        """Regression: was 2-arg (severity, tool) but tool was unused."""
        # This would raise TypeError if signature still has 2 required args
        _normalize_severity("error")


# ── Ruff status field ────────────────────────────────────────


@pytest.mark.parametrize(
    ("stable", "removed", "deprecated"),
    [
        ("stable", "removed", "deprecated"),
        ({"Stable": {}}, {"Removed": {"since": "0.5.0"}}, {"Deprecated": {"since": "0.5.0"}}),
    ],
)
def test_ruff_filters_removed_and_deprecated_rules(
    stable: str | dict[str, object], removed: str | dict[str, object], deprecated: str | dict[str, object]
) -> None:
    rules = [
        {"code": "E501", "status": stable},
        {"code": "E123", "status": removed},
        {"code": "E234", "status": deprecated},
        {"code": None, "linter": None, "status": {"Preview": {"since": "0.17.0"}}},
        {"code": "E502", "status": {}},
        {"code": "E503"},
    ]
    responses = [
        CompletedProcess([], 0, stdout=json.dumps(rules)),
        CompletedProcess([], 0, stdout="ruff 0.15.4"),
    ]
    with patch.object(_mod.subprocess, "run", side_effect=responses):
        result = _mod.extract_ruff()
    assert result["rule_count"] == 4
    assert [rule["id"] for rule in result["rules"]] == ["E501", None, "E502", "E503"]
    assert result["rules"][1]["category"] is None


def test_ruff_rejects_invalid_status() -> None:
    responses = [
        CompletedProcess([], 0, stdout='[{"code": "E501", "status": ["stable"]}]'),
        CompletedProcess([], 0, stdout="ruff 0.15.4"),
    ]
    with (
        patch.object(_mod.subprocess, "run", side_effect=responses),
        pytest.raises(ValidationError, match=r"0\.status"),
    ):
        _mod.extract_ruff()


# ── Semgrep ──────────────────────────────────────────────────


class TestSemgrep:
    def test_parses_custom_rules(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "semgrep-rules"
        rules_dir.mkdir()
        (rules_dir / "empty.yml").touch()
        (rules_dir / "sequence.yml").write_text("- not a rule document\n")
        (rules_dir / "test.yml").write_text(
            """rules:
  - id: coding-standards.test-rule
    message: |
      This is a test rule
      Only the first line goes in the catalog.
    severity: WARNING
    languages: [python]
    pattern: print(...)
  - id: coding-standards.defaults
"""
        )
        result = extract_semgrep(tmp_path)
        assert result == {
            "version": "custom",
            "rule_count": 2,
            "rules": [
                {
                    "id": "coding-standards.test-rule",
                    "summary": "This is a test rule",
                    "category": "test",
                    "severity": "warning",
                },
                {
                    "id": "coding-standards.defaults",
                    "summary": "",
                    "category": "test",
                    "severity": "warning",
                },
            ],
        }

    def test_empty_dir(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "semgrep-rules"
        rules_dir.mkdir()
        result = extract_semgrep(tmp_path)
        assert result["rule_count"] == 0

    @pytest.mark.parametrize(
        ("yaml_text", "field"),
        [
            ("rules: null", "Input should be a valid list"),
            ("rules: [false]", "\n0\n"),
            ("rules: [{id: 123}]", "0.id"),
            ("rules: [{id: test, message: null}]", "0.message"),
        ],
    )
    def test_invalid_rule_reports_filename_and_field(self, tmp_path: Path, yaml_text: str, field: str) -> None:
        rules_dir = tmp_path / "semgrep-rules"
        rules_dir.mkdir()
        (rules_dir / "invalid.yml").write_text(yaml_text)
        with pytest.raises(ValueError, match=r"Invalid Semgrep rules in .*invalid\.yml") as error:
            extract_semgrep(tmp_path)
        assert error.value.__cause__ is not None
        assert field in str(error.value.__cause__)

    def test_missing_dir(self, tmp_path: Path) -> None:
        result = extract_semgrep(tmp_path)
        assert result["rule_count"] == 0
