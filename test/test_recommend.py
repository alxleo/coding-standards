"""Tests for scripts/recommend.py."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def _run_recommend(workspace: Path) -> dict:
    """Run recommend.py against a workspace and parse JSON output."""
    result = subprocess.run(
        ["python3", "scripts/recommend.py", str(workspace)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


class TestRecommendDetection:
    def test_empty_repo_has_recommendations(self, tmp_path: Path) -> None:
        output = _run_recommend(tmp_path)
        assert output["status"] in ("recommendations_available", "fully_configured")

    def test_python_repo_recommends_pyright(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("x = 1\n")
        output = _run_recommend(tmp_path)
        tools = [r["tool"] for r in output["recommendations"]]
        assert "pyright" in tools

    def test_python_repo_with_pyright_skips(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("x = 1\n")
        (tmp_path / "pyrightconfig.json").write_text("{}\n")
        output = _run_recommend(tmp_path)
        tools = [r["tool"] for r in output["recommendations"]]
        assert "pyright" not in tools

    def test_compose_repo_recommends_conftest(self, tmp_path: Path) -> None:
        (tmp_path / "docker-compose.yml").write_text("services:\n  web:\n    image: nginx\n")
        output = _run_recommend(tmp_path)
        tools = [r["tool"] for r in output["recommendations"]]
        assert "conftest" in tools

    def test_compose_with_conftest_skips(self, tmp_path: Path) -> None:
        (tmp_path / "docker-compose.yml").write_text("services:\n  web:\n    image: nginx\n")
        (tmp_path / "conftest.toml").write_text('parser = "yaml"\n')
        output = _run_recommend(tmp_path)
        tools = [r["tool"] for r in output["recommendations"]]
        assert "conftest" not in tools

    def test_js_repo_recommends_eslint(self, tmp_path: Path) -> None:
        (tmp_path / "app.js").write_text("console.log('hi');\n")
        output = _run_recommend(tmp_path)
        tools = [r["tool"] for r in output["recommendations"]]
        assert "eslint" in tools

    def test_shell_repo_recommends_shellcheck(self, tmp_path: Path) -> None:
        (tmp_path / "run.sh").write_text("#!/bin/bash\necho hi\n")
        output = _run_recommend(tmp_path)
        tools = [r["tool"] for r in output["recommendations"]]
        assert "shellcheck" in tools

    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("x = 1\n")
        output = _run_recommend(tmp_path)
        assert "recommendations" in output
        assert isinstance(output["recommendations"], list)

    def test_each_recommendation_has_required_fields(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("x = 1\n")
        output = _run_recommend(tmp_path)
        for rec in output["recommendations"]:
            assert "tool" in rec
            assert "reason" in rec
            assert "value" in rec
            assert "setup" in rec


class TestBakedChecks:
    """Tests for the baked_checks section derived from source files."""

    def test_baked_checks_present_in_output(self, tmp_path: Path) -> None:
        output = _run_recommend(tmp_path)
        assert "baked_checks" in output
        assert "semgrep_rules" in output["baked_checks"]
        assert "conftest_policies" in output["baked_checks"]

    def test_semgrep_rules_not_empty(self, tmp_path: Path) -> None:
        output = _run_recommend(tmp_path)
        rules = output["baked_checks"]["semgrep_rules"]
        assert len(rules) > 0, "Should discover semgrep rules from source files"

    def test_semgrep_rule_has_required_fields(self, tmp_path: Path) -> None:
        output = _run_recommend(tmp_path)
        for rule in output["baked_checks"]["semgrep_rules"]:
            assert "id" in rule
            assert "message" in rule
            assert "file" in rule
            assert rule["id"].startswith("coding-standards.")

    def test_semgrep_rules_from_known_file(self, tmp_path: Path) -> None:
        """The complexity.yml file should produce at least one rule."""
        output = _run_recommend(tmp_path)
        files = {r["file"] for r in output["baked_checks"]["semgrep_rules"]}
        assert "complexity.yml" in files

    def test_conftest_policies_not_empty(self, tmp_path: Path) -> None:
        output = _run_recommend(tmp_path)
        policies = output["baked_checks"]["conftest_policies"]
        assert len(policies) > 0, "Should discover conftest policies from source files"

    def test_conftest_policy_has_required_fields(self, tmp_path: Path) -> None:
        output = _run_recommend(tmp_path)
        for policy in output["baked_checks"]["conftest_policies"]:
            assert "package" in policy
            assert "types" in policy
            assert "file" in policy
            assert isinstance(policy["types"], list)
            assert all(t in ("deny", "warn") for t in policy["types"])

    def test_conftest_excludes_test_files(self, tmp_path: Path) -> None:
        output = _run_recommend(tmp_path)
        files = {p["file"] for p in output["baked_checks"]["conftest_policies"]}
        test_files = {f for f in files if f.endswith("_test.rego")}
        assert not test_files, f"Test files should be excluded: {test_files}"

    def test_conftest_excludes_helper_only_files(self, tmp_path: Path) -> None:
        """helpers.rego has no deny/warn rules, should not appear."""
        output = _run_recommend(tmp_path)
        files = {p["file"] for p in output["baked_checks"]["conftest_policies"]}
        assert "helpers.rego" not in files

    def test_conftest_includes_compose_and_repo_standards(self, tmp_path: Path) -> None:
        output = _run_recommend(tmp_path)
        packages = {p["package"] for p in output["baked_checks"]["conftest_policies"]}
        assert any(p.startswith("compose.") for p in packages)
        assert any(p.startswith("repo_standards.") for p in packages)

    def test_healthcheck_policy_has_deny_and_warn(self, tmp_path: Path) -> None:
        """healthcheck.rego has both deny and warn rules."""
        output = _run_recommend(tmp_path)
        healthcheck = [p for p in output["baked_checks"]["conftest_policies"] if p["package"] == "compose.healthcheck"]
        assert len(healthcheck) == 1
        assert "deny" in healthcheck[0]["types"]
        assert "warn" in healthcheck[0]["types"]
