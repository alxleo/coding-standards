"""Tests for scripts/ci/summary.py."""

from __future__ import annotations

from unittest.mock import patch

import summary


def make_env(logdir: str, summary_path: str = "") -> dict[str, str]:
    return {"LINT_LOG_DIR": logdir, "GITHUB_STEP_SUMMARY": summary_path}


class TestSummaryAllPass:
    def test_exits_0(self, tmp_path):
        env = make_env(str(tmp_path))
        for group in ["hygiene", "cruft", "python", "yaml"]:
            (tmp_path / f"{group}.outcome").write_text("success")

        with patch.dict("os.environ", env), patch.object(summary, "LOGDIR", tmp_path):
            summary.main()  # Should not raise

    def test_prints_all_checks_passed(self, tmp_path, capsys):
        env = make_env(str(tmp_path))
        for group in ["hygiene", "cruft", "python"]:
            (tmp_path / f"{group}.outcome").write_text("success")

        with patch.dict("os.environ", env), patch.object(summary, "LOGDIR", tmp_path):
            summary.main()

        out = capsys.readouterr().out
        assert "All checks passed" in out

    def test_step_summary_shows_checkmark(self, tmp_path):
        summary_file = tmp_path / "summary.md"
        env = make_env(str(tmp_path), str(summary_file))
        for group in ["hygiene", "cruft"]:
            (tmp_path / f"{group}.outcome").write_text("success")

        with patch.dict("os.environ", env), patch.object(summary, "LOGDIR", tmp_path):
            summary.main()

        content = summary_file.read_text()
        assert "white_check_mark" in content


class TestSummaryFailure:
    def test_exits_1_on_failure(self, tmp_path):
        env = make_env(str(tmp_path))
        (tmp_path / "hygiene.outcome").write_text("success")
        (tmp_path / "python.outcome").write_text("failure")
        (tmp_path / "python.log").write_text("src/main.py:1:1: E302\n")

        with patch.dict("os.environ", env), patch.object(summary, "LOGDIR", tmp_path):
            try:
                summary.main()
                raise AssertionError("Should have exited with code 1")
            except SystemExit as e:
                assert e.code == 1

    def test_table_shows_group_name_with_fail_status(self, tmp_path, capsys):
        env = make_env(str(tmp_path))
        (tmp_path / "python.outcome").write_text("failure")
        (tmp_path / "python.log").write_text("ERROR: bad\n")

        with patch.dict("os.environ", env), patch.object(summary, "LOGDIR", tmp_path):
            try:
                summary.main()
            except SystemExit:
                pass

        out = capsys.readouterr().out
        # Verify the group name appears on a line that also contains FAIL
        fail_lines = [line for line in out.splitlines() if "FAIL" in line]
        assert any("Python" in line for line in fail_lines), (
            f"Expected 'Python' on a FAIL line, got: {fail_lines}"
        )

    def test_step_summary_failure_table(self, tmp_path):
        summary_file = tmp_path / "summary.md"
        env = make_env(str(tmp_path), str(summary_file))
        (tmp_path / "python.outcome").write_text("failure")
        (tmp_path / "python.log").write_text("src/main.py:1:1: E302\n")

        with patch.dict("os.environ", env), patch.object(summary, "LOGDIR", tmp_path):
            try:
                summary.main()
            except SystemExit:
                pass

        content = summary_file.read_text()
        assert "failures detected" in content
        assert "Python" in content
        assert "| Status | Check | Detail |" in content

    def test_step_summary_has_details_block_with_errors(self, tmp_path):
        """The step summary should contain <details> blocks with error output."""
        summary_file = tmp_path / "summary.md"
        env = make_env(str(tmp_path), str(summary_file))
        (tmp_path / "python.outcome").write_text("failure")
        (tmp_path / "python.log").write_text(
            "src/main.py:1:1: E302 expected 2 blank lines\n"
        )

        with patch.dict("os.environ", env), patch.object(summary, "LOGDIR", tmp_path):
            try:
                summary.main()
            except SystemExit:
                pass

        content = summary_file.read_text()
        assert "<details>" in content
        assert "</details>" in content
        assert "```" in content
        assert "E302" in content
        # Verify code fence is properly closed (even number of ```)
        assert content.count("```") % 2 == 0, "unclosed code fence in step summary"

    def test_shows_error_detail_with_arrow(self, tmp_path, capsys):
        env = make_env(str(tmp_path))
        (tmp_path / "yaml.outcome").write_text("failure")
        (tmp_path / "yaml.log").write_text("ERROR: config.yml:3:1 wrong indentation\n")

        with patch.dict("os.environ", env), patch.object(summary, "LOGDIR", tmp_path):
            try:
                summary.main()
            except SystemExit:
                pass

        out = capsys.readouterr().out
        assert "\u21b3" in out


class TestSummarySkipped:
    def test_shows_skip_for_missing_outcomes(self, tmp_path, capsys):
        env = make_env(str(tmp_path))
        # No outcome files — everything should be "skipped"

        with patch.dict("os.environ", env), patch.object(summary, "LOGDIR", tmp_path):
            summary.main()

        out = capsys.readouterr().out
        # Verify "skip" appears in table rows (next to group names)
        skip_lines = [line for line in out.splitlines() if "skip" in line]
        assert len(skip_lines) > 0, "Expected at least one 'skip' line in output"


class TestSummaryNoStepSummary:
    def test_works_without_github_step_summary(self, tmp_path, capsys):
        env = make_env(str(tmp_path), "")
        (tmp_path / "hygiene.outcome").write_text("success")

        with patch.dict("os.environ", env), patch.object(summary, "LOGDIR", tmp_path):
            summary.main()

        out = capsys.readouterr().out
        assert "All checks passed" in out
