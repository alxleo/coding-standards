"""Tests for scripts/extract_linter_timings.py.

Uses pythonpath=["."] from pyproject.toml so `from scripts.x import y` works
in CI, locally, and in pre-commit without spec_from_file_location hacks.
"""

from pathlib import Path
from textwrap import dedent

from scripts.extract_linter_timings import parse_report_markdown

# ruff: noqa: E501 — fixture data mirrors real MegaLinter report tables
SAMPLE_REPORT = dedent("""\
## ✅⚠️[MegaLinter](https://megalinter.io/9.4.0) analysis: Success with warnings

|  Descriptor   |                                             Linter                                              |Files|Fixed|Errors|Warnings|Elapsed time|
|---------------|-------------------------------------------------------------------------------------------------|----:|----:|-----:|-------:|-----------:|
|✅ ACTION      |[actionlint](https://megalinter.io/9.4.0/descriptors/action_actionlint)                          |    4|     |     0|       0|       1.15s|
|✅ REPOSITORY  |[semgrep](https://megalinter.io/9.4.0/descriptors/repository_semgrep)                            |  yes|     |    no|      no|      25.73s|
|⚠️ EDITORCONFIG|[editorconfig-checker](https://megalinter.io/9.4.0/descriptors/editorconfig_editorconfig_checker)|  139|     |     1|       0|       0.73s|
|✅ PYTHON      |[ruff](https://megalinter.io/9.4.0/descriptors/python_ruff)                                      |   16|     |     0|       0|       0.32s|
|✅ YAML        |[v8r](https://megalinter.io/9.4.0/descriptors/yaml_v8r)                                          |   48|     |     0|       0|       16.7s|
""")


class TestParseReportMarkdown:
    def test_extracts_all_linters(self, tmp_path: Path):
        report = tmp_path / "megalinter-report.md"
        report.write_text(SAMPLE_REPORT)
        timings = parse_report_markdown(report)
        assert len(timings) == 5

    def test_file_mode_linter(self, tmp_path: Path):
        report = tmp_path / "megalinter-report.md"
        report.write_text(SAMPLE_REPORT)
        timings = parse_report_markdown(report)
        actionlint = next(t for t in timings if t["linter"] == "actionlint")
        assert actionlint["descriptor"] == "ACTION"
        assert actionlint["elapsed_s"] == 1.15
        assert actionlint["files"] == 4
        assert actionlint["errors"] == 0

    def test_project_mode_linter(self, tmp_path: Path):
        """Project-mode linters show 'yes'/'no' instead of counts."""
        report = tmp_path / "megalinter-report.md"
        report.write_text(SAMPLE_REPORT)
        timings = parse_report_markdown(report)
        semgrep = next(t for t in timings if t["linter"] == "semgrep")
        assert semgrep["files"] == -1  # "yes" → -1
        assert semgrep["errors"] == 0  # "no" → 0
        assert semgrep["elapsed_s"] == 25.73

    def test_linter_with_errors(self, tmp_path: Path):
        report = tmp_path / "megalinter-report.md"
        report.write_text(SAMPLE_REPORT)
        timings = parse_report_markdown(report)
        ec = next(t for t in timings if t["linter"] == "editorconfig-checker")
        assert ec["errors"] == 1
        assert ec["files"] == 139

    def test_decimal_elapsed_time(self, tmp_path: Path):
        report = tmp_path / "megalinter-report.md"
        report.write_text(SAMPLE_REPORT)
        timings = parse_report_markdown(report)
        v8r = next(t for t in timings if t["linter"] == "v8r")
        assert v8r["elapsed_s"] == 16.7

    def test_empty_report(self, tmp_path: Path):
        report = tmp_path / "megalinter-report.md"
        report.write_text("# No table here\n")
        timings = parse_report_markdown(report)
        assert timings == []
