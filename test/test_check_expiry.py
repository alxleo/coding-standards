"""Tests for scripts/ci/check-expiry.py."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Import the hyphenated module via importlib
_spec = importlib.util.spec_from_file_location(
    "check_expiry",
    Path(__file__).resolve().parent.parent / "scripts" / "ci" / "check-expiry.py",
)
assert _spec is not None and _spec.loader is not None
check_expiry = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_expiry)

SCRIPT = str(
    Path(__file__).resolve().parent.parent / "scripts" / "ci" / "check-expiry.py"
)
TODAY = datetime.now(tz=UTC).date()
PAST = TODAY - timedelta(days=30)
FUTURE = TODAY + timedelta(days=30)


def _compile_defaults() -> list[re.Pattern]:
    return [re.compile(p) for p in check_expiry.DEFAULT_PATTERNS]


class TestScanFileRemoveAfter:
    def test_past_date_is_found(self, tmp_path):
        f = tmp_path / "test.yml"
        f.write_text(f"# REMOVE_AFTER: {PAST}\nsome content\n")
        findings = check_expiry.scan_file(f, _compile_defaults(), TODAY)
        assert len(findings) == 1
        assert str(PAST) in findings[0]
        assert "expired marker" in findings[0]

    def test_future_date_not_found(self, tmp_path):
        f = tmp_path / "test.yml"
        f.write_text(f"# REMOVE_AFTER: {FUTURE}\nsome content\n")
        findings = check_expiry.scan_file(f, _compile_defaults(), TODAY)
        assert len(findings) == 0


class TestScanFileTodo:
    def test_past_todo_is_found(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(f"# TODO({PAST}) clean up this hack\n")
        findings = check_expiry.scan_file(f, _compile_defaults(), TODAY)
        assert len(findings) == 1
        assert str(PAST) in findings[0]


class TestScanFileDeprecateBy:
    def test_past_deprecate_is_found(self, tmp_path):
        f = tmp_path / "test.sh"
        f.write_text(f"# DEPRECATE_BY: {PAST}\nold_function()\n")
        findings = check_expiry.scan_file(f, _compile_defaults(), TODAY)
        assert len(findings) == 1
        assert str(PAST) in findings[0]


class TestScanFileNoMarkers:
    def test_no_markers_returns_empty(self, tmp_path):
        f = tmp_path / "clean.yml"
        f.write_text("name: workflow\non:\n  push:\n")
        findings = check_expiry.scan_file(f, _compile_defaults(), TODAY)
        assert len(findings) == 0


class TestScanFileMultiple:
    def test_multiple_expired_markers_counted(self, tmp_path):
        f = tmp_path / "multi.py"
        f.write_text(
            f"# REMOVE_AFTER: {PAST}\n"
            f"# TODO({PAST}) fix this\n"
            f"# DEPRECATE_BY: {PAST}\n"
            f"# REMOVE_AFTER: {FUTURE}\n"  # not expired
        )
        findings = check_expiry.scan_file(f, _compile_defaults(), TODAY)
        assert len(findings) == 3


class TestCustomPattern:
    def test_custom_pattern_via_subprocess(self, tmp_path):
        f = tmp_path / "test.yml"
        f.write_text(f"# SUNSET: {PAST}\n")
        result = subprocess.run(
            [
                sys.executable,
                SCRIPT,
                str(tmp_path),
                "--pattern",
                r"SUNSET:\s*(\d{4}-\d{2}-\d{2})",
                "--ext",
                ".yml",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1
        assert "expired marker" in result.stdout
        assert str(PAST) in result.stdout
