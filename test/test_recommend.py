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
