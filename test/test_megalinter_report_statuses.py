"""Tests for megalinter_report_statuses.py (commit status posting)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = str(
    Path(__file__).resolve().parent.parent / "scripts" / "megalinter_report_statuses.py"
)


def _make_report(tmp_path: Path, linters: list[dict]) -> Path:
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"linters": linters}))
    return report


def _run(report_path: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, SCRIPT, report_path],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class TestMissingEnvVars:
    def test_exits_with_message_when_no_token(self, tmp_path):
        report = _make_report(tmp_path, [])
        result = _run(
            str(report),
            env={
                "PATH": "",
                "GITHUB_REPOSITORY": "test/repo",
                "GITHUB_SHA": "abc123",
            },
        )
        assert result.returncode == 1
        assert "Missing" in result.stdout

    def test_exits_with_message_when_no_repo(self, tmp_path):
        report = _make_report(tmp_path, [])
        result = _run(
            str(report),
            env={
                "PATH": "",
                "GITHUB_TOKEN": "test-token",
                "GITHUB_SHA": "abc123",
            },
        )
        assert result.returncode == 1
        assert "Missing" in result.stdout

    def test_exits_with_message_when_no_sha(self, tmp_path):
        report = _make_report(tmp_path, [])
        result = _run(
            str(report),
            env={
                "PATH": "",
                "GITHUB_TOKEN": "test-token",
                "GITHUB_REPOSITORY": "test/repo",
            },
        )
        assert result.returncode == 1
        assert "Missing" in result.stdout


class TestPassingLinter:
    def test_prints_success(self, tmp_path):
        """A linter with return_code 0 should print success with checkmark."""
        report = _make_report(
            tmp_path,
            [
                {
                    "linter_name": "YAML_YAMLLINT",
                    "is_active": True,
                    "return_code": 0,
                    "total_number_errors": 0,
                    "total_number_warnings": 0,
                    "elapsed_time_s": 1.2,
                }
            ],
        )
        # The script will fail on the HTTP POST, but we can still check stdout
        # before that by providing env vars but no real endpoint
        result = _run(
            str(report),
            env={
                "PATH": "",
                "GITHUB_TOKEN": "test-token",
                "GITHUB_REPOSITORY": "test/repo",
                "GITHUB_SHA": "abc123",
                "GITHUB_SERVER_URL": "https://github.com",
            },
        )
        # The script will attempt to POST and fail with a connection error,
        # but it still prints the status line
        assert "YAML_YAMLLINT" in result.stdout
        assert "success" in result.stdout


class TestFailingLinter:
    def test_prints_failure(self, tmp_path):
        """A linter with return_code != 0 should print failure with X mark."""
        report = _make_report(
            tmp_path,
            [
                {
                    "linter_name": "PYTHON_RUFF",
                    "is_active": True,
                    "return_code": 1,
                    "total_number_errors": 3,
                    "total_number_warnings": 0,
                    "elapsed_time_s": 2.5,
                }
            ],
        )
        result = _run(
            str(report),
            env={
                "PATH": "",
                "GITHUB_TOKEN": "test-token",
                "GITHUB_REPOSITORY": "test/repo",
                "GITHUB_SHA": "abc123",
                "GITHUB_SERVER_URL": "https://github.com",
            },
        )
        assert "PYTHON_RUFF" in result.stdout
        assert "failure" in result.stdout
