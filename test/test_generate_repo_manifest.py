"""Tests for generate-repo-manifest.py.

Uses a temporary directory as a fixture repo to verify manifest output.
Pydantic validation runs inside generate() — if the manifest is structurally
wrong, generate() itself raises ValidationError.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# Import from hyphenated filename
_script = Path(__file__).resolve().parent.parent / "scripts" / "generate-repo-manifest.py"
_spec = importlib.util.spec_from_file_location("generate_repo_manifest", _script)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["generate_repo_manifest"] = _mod

# manifest_schema must be importable for the generator
sys.path.insert(0, str(_script.parent))
_spec.loader.exec_module(_mod)

generate = _mod.generate


@pytest.fixture
def empty_repo(tmp_path: Path) -> Path:
    """Minimal repo — no files at all."""
    return tmp_path


@pytest.fixture
def python_repo(tmp_path: Path) -> Path:
    """Repo with Python files, tests, and pyproject.toml."""
    (tmp_path / "app.py").write_text("print('hello')\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text("def test_it(): pass\n")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test"\n[project.optional-dependencies]\ntest = ["pytest", "pytest-randomly"]\n'
    )
    (tmp_path / "pyrightconfig.json").write_text("{}\n")
    (tmp_path / "ruff.toml").write_text("[lint]\nselect = []\n")
    return tmp_path


@pytest.fixture
def js_repo(tmp_path: Path) -> Path:
    """Repo with JS/TS files."""
    (tmp_path / "index.ts").write_text("console.log('hello');\n")
    (tmp_path / "package.json").write_text('{"devDependencies": {"zod": "3.0.0"}}\n')
    (tmp_path / "tsconfig.json").write_text("{}\n")
    (tmp_path / ".nvmrc").write_text("22\n")
    return tmp_path


def test_empty_repo_produces_valid_manifest(empty_repo: Path) -> None:
    """generate() on empty dir should not raise (Pydantic validates internally)."""
    manifest = generate(empty_repo)
    assert manifest["content"]["python_files"] == 0
    assert manifest["files"]["pyrightconfig"] is False


def test_python_repo_detects_files(python_repo: Path) -> None:
    manifest = generate(python_repo)
    assert manifest["content"]["python_files"] == 2  # app.py + test_app.py
    assert manifest["files"]["pyrightconfig"] is True
    assert manifest["files"]["ruff"] is True
    assert manifest["directories"]["tests"] is True
    assert manifest["dependencies"]["pytest_randomly"] is True
    assert manifest["dependencies"]["test_deps_defined"] is True


def test_js_repo_detects_files(js_repo: Path) -> None:
    manifest = generate(js_repo)
    assert manifest["content"]["typescript_files"] == 1
    assert manifest["files"]["tsconfig"] is True
    assert manifest["files"]["nvmrc"] is True
    assert manifest["dependencies"]["zod"] is True


def test_acknowledged_string_passes_through(tmp_path: Path) -> None:
    (tmp_path / ".repo-standards.yml").write_text(
        "acknowledged:\n  pydantic: 'not needed'\n"
    )
    manifest = generate(tmp_path)
    assert manifest["acknowledged"]["pydantic"] == "not needed"


def test_acknowledged_expired_stripped(tmp_path: Path) -> None:
    (tmp_path / ".repo-standards.yml").write_text(
        "acknowledged:\n  pydantic:\n    reason: 'will fix'\n    expires: '2020-01-01'\n"
    )
    manifest = generate(tmp_path)
    assert "pydantic" not in manifest["acknowledged"]


def test_acknowledged_not_expired_kept(tmp_path: Path) -> None:
    (tmp_path / ".repo-standards.yml").write_text(
        "acknowledged:\n  pydantic:\n    reason: 'will fix'\n    expires: '2099-01-01'\n"
    )
    manifest = generate(tmp_path)
    assert "pydantic" in manifest["acknowledged"]


def test_large_shell_scripts_counted(tmp_path: Path) -> None:
    (tmp_path / "big.sh").write_text("#!/bin/bash\n" + "echo hi\n" * 60)
    (tmp_path / "small.sh").write_text("#!/bin/bash\necho hi\n")
    manifest = generate(tmp_path)
    assert manifest["content"]["shell_scripts_over_50_lines"] == 1


def test_large_shell_per_file_acknowledged(tmp_path: Path) -> None:
    (tmp_path / "big.sh").write_text("#!/bin/bash\n" + "echo hi\n" * 60)
    (tmp_path / ".repo-standards.yml").write_text(
        "acknowledged:\n  large_shell_scripts:\n    - path: big.sh\n      reason: intentional\n"
    )
    manifest = generate(tmp_path)
    assert manifest["content"]["shell_scripts_over_50_lines"] == 0


def test_suppressions_counted(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("x = 1  # noqa: E501\ny = 2  # type: ignore\n")
    manifest = generate(tmp_path)
    assert manifest["suppressions"]["noqa"] == 1
    assert manifest["suppressions"]["type_ignore"] == 1
    assert manifest["suppressions"]["total"] >= 2


def test_compose_files_recursive(tmp_path: Path) -> None:
    (tmp_path / "docker-compose.yml").write_text("services:\n")
    infra = tmp_path / "infra"
    infra.mkdir()
    (infra / "docker-compose.prod.yml").write_text("services:\n")
    manifest = generate(tmp_path)
    assert manifest["content"]["compose_files"] == 2
