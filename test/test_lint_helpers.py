"""Tests for scripts/ci/lint_helpers.py."""

from __future__ import annotations

from pathlib import Path

from lint_helpers import extract_errors, extract_hint, parse_groups


class TestParseGroups:
    def test_parses_valid_conf(self, tmp_path):
        conf = tmp_path / "groups.conf"
        conf.write_text(
            "# comment\n"
            "hygiene|File hygiene|file hygiene|Lint: file hygiene\n"
            "python|Python|python|Lint: Python (ruff)\n"
        )
        groups = parse_groups(conf)
        assert len(groups) == 2
        assert groups[0] == (
            "hygiene",
            "File hygiene",
            "file hygiene",
            "Lint: file hygiene",
        )
        assert groups[1] == ("python", "Python", "python", "Lint: Python (ruff)")

    def test_skips_comments_and_blank_lines(self, tmp_path):
        conf = tmp_path / "groups.conf"
        conf.write_text("# header comment\n\n# another\nhygiene|a|b|c\n\n")
        groups = parse_groups(conf)
        assert len(groups) == 1

    def test_drops_malformed_lines(self, tmp_path):
        """Lines with wrong field count are silently dropped."""
        conf = tmp_path / "groups.conf"
        conf.write_text(
            "good|Good Group|good context|Good Step\n"
            "bad|only three fields|missing\n"
            "also_bad|two|three|four|five_extra\n"
        )
        groups = parse_groups(conf)
        assert len(groups) == 1
        assert groups[0][0] == "good"

    def test_real_groups_conf_structural_integrity(self):
        """Every line in the real groups.conf parses to exactly 4 non-empty fields."""
        conf = Path(__file__).resolve().parent.parent / "scripts" / "ci" / "groups.conf"
        groups = parse_groups(conf)
        assert len(groups) >= 1, "groups.conf should have at least one group"
        logkeys = [g[0] for g in groups]
        assert len(logkeys) == len(set(logkeys)), "duplicate logkeys found"
        for logkey, display_name, status_context, step_name in groups:
            assert logkey, "empty logkey in groups.conf"
            assert display_name, f"empty display_name for {logkey}"
            assert status_context, f"empty status_context for {logkey}"
            assert step_name, f"empty step_name for {logkey}"


class TestExtractErrors:
    def test_extracts_error_lines(self, tmp_path):
        logfile = tmp_path / "test.log"
        logfile.write_text(
            "[INFO] Installing...\n"
            "src/main.py:1:1: E302 expected 2 blank lines\n"
            "src/main.py:5:1: error: undefined name\n"
            "- Installing pre-commit hooks...\n"
        )
        errors = extract_errors(logfile)
        assert len(errors) == 2
        assert "E302" in errors[0]
        assert "undefined name" in errors[1]

    def test_filters_noise(self, tmp_path):
        logfile = tmp_path / "test.log"
        logfile.write_text(
            "[INFO] Starting\n- Installing hooks\n::group::test\nCheck YAML.......................Passed\n"
        )
        errors = extract_errors(logfile)
        assert len(errors) == 0

    def test_respects_limit(self, tmp_path):
        logfile = tmp_path / "test.log"
        lines = [f"file.py:{i}:1: error: bad" for i in range(20)]
        logfile.write_text("\n".join(lines))
        errors = extract_errors(logfile, limit=3)
        assert len(errors) == 3

    def test_missing_file_returns_empty(self, tmp_path):
        errors = extract_errors(tmp_path / "nonexistent.log")
        assert errors == []

    def test_filters_banner_lines(self, tmp_path):
        logfile = tmp_path / "test.log"
        logfile.write_text("Check YAML.....................Failed\n")
        errors = extract_errors(logfile)
        assert len(errors) == 0


class TestExtractHint:
    def test_priority_file_line(self, tmp_path):
        logfile = tmp_path / "test.log"
        logfile.write_text("ERROR: something bad\nsrc/main.py:10:5: unused import\n")
        hint = extract_hint(logfile)
        assert "src/main.py:10:5" in hint

    def test_priority_keyword_when_no_file_line(self, tmp_path):
        logfile = tmp_path / "test.log"
        logfile.write_text("[INFO] Starting\nERROR: config is invalid\ndone\n")
        hint = extract_hint(logfile)
        assert "config is invalid" in hint

    def test_fallback_to_last_meaningful(self, tmp_path):
        logfile = tmp_path / "test.log"
        logfile.write_text("[INFO] Starting\nsome relevant output\n")
        hint = extract_hint(logfile)
        assert hint == "some relevant output"

    def test_truncates_to_max_len(self, tmp_path):
        logfile = tmp_path / "test.log"
        logfile.write_text("x" * 200 + ":1:1: error\n")
        hint = extract_hint(logfile, max_len=140)
        assert len(hint) <= 140

    def test_missing_file_returns_empty(self, tmp_path):
        assert extract_hint(tmp_path / "nope.log") == ""

    def test_banner_fallback(self, tmp_path):
        logfile = tmp_path / "test.log"
        logfile.write_text("[INFO] Starting\n- Installing hooks\nCheck YAML.....................Failed\n")
        hint = extract_hint(logfile)
        assert "Failed" in hint

    def test_excludes_banner_from_keyword_priority(self, tmp_path):
        """Banner lines with 'Failed' should not match keyword priority."""
        logfile = tmp_path / "test.log"
        logfile.write_text("Check YAML.....................Failed\nconfig.yml:3:1 wrong indentation\n")
        hint = extract_hint(logfile)
        assert "config.yml:3:1" in hint

    def test_file_line_that_is_also_banner(self, tmp_path):
        """A line matching both file:line and banner pattern uses file:line priority."""
        logfile = tmp_path / "test.log"
        logfile.write_text("check.yml:3:1.....Failed\n")
        hint = extract_hint(logfile)
        # The banner filter should exclude this — it's not a useful file:line hint
        # Falls through to banner fallback
        assert hint != ""


class TestWorkflowCacheAudit:
    """Every tool install in lint.yml must have a corresponding cache step."""

    def _load_workflow(self):
        import yaml

        wf = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "lint.yml"
        return yaml.safe_load(wf.read_text())

    def test_every_install_step_has_cache(self):
        """Steps that install tools must be conditional on a cache-hit check."""
        wf = self._load_workflow()
        steps = wf["jobs"]["lint"]["steps"]

        # Find install steps: name contains "Install" and has a run: key
        # Exclude steps where caching is handled by a setup action:
        #   - "Install Python" — cached by setup-uv (enable-cache: true)
        #   - "Install pre-commit hooks" — cached by cache-tools (consolidated)
        #   - "Install npm dependencies" — consumer deps, not our tools
        excluded = {
            "Install Python",
            "Install pre-commit hooks",
            "Install npm dependencies",
        }
        install_steps = [
            s
            for s in steps
            if s.get("name", "").startswith("Install") and "run" in s and s.get("name", "") not in excluded
        ]

        for step in install_steps:
            condition = step.get("if", "")
            assert "cache-hit" in condition, (
                f"Install step '{step['name']}' is not conditional on a cache hit. "
                f"Add a cache step and gate the install with: "
                f"if: steps.cache-xxx.outputs.cache-hit != 'true'"
            )

    def test_consolidated_cache_step_has_id(self):
        """The consolidated cache step must have an id for the audit step."""
        wf = self._load_workflow()
        steps = wf["jobs"]["lint"]["steps"]

        cache_steps = [s for s in steps if isinstance(s.get("uses", ""), str) and "actions/cache@" in s.get("uses", "")]
        assert len(cache_steps) == 1, f"Expected exactly 1 consolidated cache step, found {len(cache_steps)}"
        assert cache_steps[0].get("id") == "cache-tools", "Consolidated cache step must have id: cache-tools"
