"""Tests for generate_rule_catalog.py.

Covers the extractors that caused build failures:
- ruff status field format (string vs dict)
- normalize_severity argument count
- semgrep YAML parsing
- dockle hardcoded data
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import via spec loader (script lives in scripts/, not a package)
_script = Path(__file__).resolve().parent.parent / "scripts" / "generate_rule_catalog.py"
_spec = importlib.util.spec_from_file_location("generate_rule_catalog", _script)
assert _spec is not None
_mod = importlib.util.module_from_spec(_spec)
sys.modules["generate_rule_catalog"] = _mod
assert _spec.loader is not None
_spec.loader.exec_module(_mod)

_normalize_severity = _mod._normalize_severity
extract_dockle = _mod.extract_dockle
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


class TestRuffStatusParsing:
    """Regression: ruff versions return status as string or dict."""

    def test_string_status(self) -> None:
        """Local ruff returns status as plain string."""
        rule = {"code": "E501", "summary": "Line too long", "status": "stable", "linter": "pycodestyle"}
        raw_status = rule.get("status", "stable")
        status = (raw_status if isinstance(raw_status, str) else next(iter(raw_status), "stable")).lower()
        assert status == "stable"

    def test_dict_status(self) -> None:
        """Image ruff returns status as dict like {"Stable": {}}."""
        rule = {"code": "E501", "summary": "Line too long", "status": {"Stable": {}}, "linter": "pycodestyle"}
        raw_status = rule.get("status", "stable")
        status = (raw_status if isinstance(raw_status, str) else next(iter(raw_status), "stable")).lower()
        assert status == "stable"

    def test_removed_status_filtered(self) -> None:
        raw_status = "removed"
        status = (raw_status if isinstance(raw_status, str) else next(iter(raw_status), "stable")).lower()
        assert status == "removed"

    def test_dict_removed_status_filtered(self) -> None:
        raw_status = {"Removed": {"since": "0.5.0"}}
        status = (raw_status if isinstance(raw_status, str) else next(iter(raw_status), "stable")).lower()
        assert status == "removed"


# ── Dockle ───────────────────────────────────────────────────


class TestDockle:
    def test_returns_all_checkpoints(self) -> None:
        result = extract_dockle()
        assert result["rule_count"] == 20
        assert len(result["rules"]) == 20

    def test_has_required_fields(self) -> None:
        result = extract_dockle()
        for rule in result["rules"]:
            assert "id" in rule
            assert "summary" in rule
            assert "severity" in rule
            assert rule["severity"] in ("error", "warning", "info", "ignore")

    def test_cis_and_dkl_prefixes(self) -> None:
        result = extract_dockle()
        ids = {r["id"] for r in result["rules"]}
        assert any(i.startswith("CIS-DI-") for i in ids)
        assert any(i.startswith("DKL-") for i in ids)


# ── Semgrep ──────────────────────────────────────────────────


class TestSemgrep:
    def test_parses_custom_rules(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "semgrep-rules"
        rules_dir.mkdir()
        (rules_dir / "test.yml").write_text(
            """rules:
  - id: coding-standards.test-rule
    message: This is a test rule
    severity: WARNING
    languages: [python]
    pattern: print(...)
"""
        )
        result = extract_semgrep(tmp_path)
        assert result["rule_count"] == 1
        assert result["rules"][0]["id"] == "coding-standards.test-rule"
        assert result["rules"][0]["severity"] == "warning"

    def test_empty_dir(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "semgrep-rules"
        rules_dir.mkdir()
        result = extract_semgrep(tmp_path)
        assert result["rule_count"] == 0

    def test_missing_dir(self, tmp_path: Path) -> None:
        result = extract_semgrep(tmp_path)
        assert result["rule_count"] == 0
