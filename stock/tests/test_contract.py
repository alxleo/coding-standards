"""Exercise the real stock scanner and Renovate dependency contracts."""

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

import pytest

from stock.image_pins import image_pins

TESTS = Path(__file__).parent
ROOT = TESTS.parent.parent
FIXTURE = TESTS / "fixture"
EXPECTED = json.loads((TESTS / "expected.json").read_text())
LINTERS = (
    "ACTION_ZIZMOR",
    "JSON_V8R",
    "PYTHON_RUFF",
    "REPOSITORY_BETTERLEAKS",
    "REPOSITORY_SEMGREP",
    "REPOSITORY_TRIVY",
    "YAML_YAMLLINT",
)


def run(*args, cwd=None, env=None, check=True):
    return subprocess.run(args, cwd=cwd, env=env, check=check, capture_output=True, text=True, timeout=600)


def copy_fixture(stage, source):
    for path in stage.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(stage)
        target = source / relative.with_name(path.name.removesuffix(".fixture"))
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.name.endswith("-token.txt"):
            # Generate a recognizable but fictitious token only inside the test repo.
            value = "ghp_" + hashlib.sha256(target.name.encode()).hexdigest()[:36]
            target.write_text(path.read_text().replace("TOKEN_PLACEHOLDER", value))
        else:
            shutil.copyfile(path, target)


def commit(source):
    run("git", "add", "--all", cwd=source)
    run(
        "git",
        "-c",
        "user.name=Stock Contract",
        "-c",
        "user.email=stock@example.com",
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "-m",
        "Stock contract fixture",
        cwd=source,
    )
    return run("git", "rev-parse", "HEAD", cwd=source).stdout.strip()


def scan(source, reports, cache, *options, linters=LINTERS):
    result = run(
        "uv",
        "run",
        "--script",
        str(ROOT / "stock/containers.py"),
        "--source",
        str(source),
        "--reports",
        str(reports),
        "--cache",
        str(cache),
        "--persistent",
        "--consumer-config",
        ".mega-linter.yml",
        "--trivy-config",
        "policy/trivy.yml",
        "--semgrep-config",
        "policy/semgrep.yml",
        "--semgrep-targets",
        ":(glob)tests/**/*.py",
        *(option for key in linters for option in ("--linter", key)),
        *options,
        check=False,
    )
    assert (reports / "containers.json").is_file(), result.stderr[-10000:]
    return result.returncode, json.loads((reports / "containers.json").read_text())


def sarif_findings(key, report):
    for entry in report["runs"]:
        for result in entry.get("results", []):
            for location in result.get("locations", []):
                uri = location["physicalLocation"]["artifactLocation"]["uri"]
                uri_path = urlsplit(uri)
                path = unquote(uri_path.path or uri_path.netloc).removeprefix("/tmp/lint/").removeprefix("./")
                yield key, path, result["ruleId"]


def json_findings(key, report):
    # These pinned adapters report diagnostics only in MegaLinter's detailed JSON.
    for linter in report["active_linters"]:
        output = linter["stdout"]
        if key == "JSON_V8R":
            for match in re.finditer(r"^(.+?)#(\S+) (.+)$", output, re.MULTILINE):
                yield key, match[1], f"{match[2]} {match[3]}"
        elif key == "YAML_YAMLLINT":
            for block in output.strip().split("\n\n"):
                path, _, diagnostics = block.partition("\n")
                for rule in re.findall(r"\(([^()]+)\)$", diagnostics, re.MULTILINE):
                    yield key, path.strip(), rule


def findings(directory):
    rows = set()
    for linter in directory.iterdir():
        if not linter.is_dir():
            continue
        key = linter.name.upper()
        if key == "REPOSITORY_SEMGREP_LOCAL":
            data = json.loads((linter / "findings.json").read_text())
            rows.update((key, item["path"], item["check_id"]) for item in data["results"])
        elif key == "ACTION_ZIZMOR":
            data = json.loads((linter / "console.log").read_text())
            for item in data:
                paths = {location["symbolic"]["key"]["Local"]["given_path"] for location in item["locations"]}
                rows.update((key, path.removeprefix("./"), item["ident"]) for path in paths)
        elif key in {"JSON_V8R", "YAML_YAMLLINT"}:
            data = json.loads((linter / "mega-linter-report.json").read_text())
            rows.update(json_findings(key, data))
        elif (report := linter / "megalinter-report.sarif").is_file():
            rows.update(sarif_findings(key, json.loads(report.read_text())))
    return sorted(map(list, rows))


def test_stock_scanners(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    run("git", "init", "--quiet", cwd=source)
    copy_fixture(FIXTURE / "base", source)
    first = commit(source)
    (source / "changed.py").write_text('marker = "allowed"\n')
    base = commit(source)
    cache = tmp_path / "cache"
    code, skipped = scan(source, tmp_path / "source-only", cache, "--base", first, linters=("REPOSITORY_TRIVY",))
    assert code == 0 and skipped["skipped_linters"] == ["REPOSITORY_TRIVY"] and skipped["linters"] == []
    copy_fixture(FIXTURE / "pr", source)
    commit(source)
    digest = image_pins()["images"]["REPOSITORY_SEMGREP"].removeprefix("sha256:")
    rules = cache / f"semgrep-{digest}"
    rules.mkdir()
    for name in ("security-audit", "trailofbits"):
        (rules / f"{name}.yaml").write_text("rules: []\n")
    observed = {}
    for mode, options in (("pr", ("--base", base)), ("full", ())):
        reports = tmp_path / mode
        code, metrics = scan(source, reports, cache, *options)
        assert code == 1
        assert {row["linter"] for row in metrics["linters"]} == {*LINTERS, "REPOSITORY_SEMGREP_LOCAL"}
        exits = {row["linter"]: row["exit"] for row in metrics["linters"]}
        assert exits["REPOSITORY_SEMGREP"] == 0, exits
        assert all(exits[key] for key in {*LINTERS, "REPOSITORY_SEMGREP_LOCAL"} - {"REPOSITORY_SEMGREP"}), exits
        observed[mode] = findings(reports)
    assert observed == EXPECTED["findings"], json.dumps(observed, indent=2)


def test_stock_inherited_policy_and_pyright_project(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    run("git", "init", "--quiet", cwd=source)
    (source / ".gitignore").write_text(".venv/\n")
    (source / ".mega-linter.yml").write_text(
        "EXTENDS:\n"
        "  - https://raw.githubusercontent.com/alxleo/coding-standards/main/.mega-linter-default.yml\n"
        "LINTER_RULES_PATH: rules\n"
        "PYTHON_PYRIGHT_CONFIG_FILE: types.json\n"
    )
    rules = source / "rules"
    rules.mkdir()
    (rules / "types.json").write_text(
        json.dumps(
            {
                "reportAssignmentType": "none",
                "reportMissingImports": "error",
                "reportUndefinedVariable": "error",
                "venvPath": "../project",
                "venv": ".venv",
            }
        )
    )
    project = source / "project"
    project.mkdir()
    package = "fixture_dependency-1.0-py3-none-any.whl"
    info = "fixture_dependency-1.0.dist-info"
    with ZipFile(source / package, "w") as wheel:
        wheel.writestr("fixture_dependency/__init__.py", "value: int = 1\n")
        wheel.writestr(f"{info}/METADATA", "Metadata-Version: 2.1\nName: fixture-dependency\nVersion: 1.0\n")
        wheel.writestr(f"{info}/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        wheel.writestr(f"{info}/RECORD", "")
    project_config = (
        '[project]\nname = "fixture"\nversion = "{version}"\nrequires-python = ">=3.11"\n'
        'dependencies = ["fixture-dependency"]\n\n[tool.uv]\npackage = false\n'
        '[tool.uv.sources]\nfixture-dependency = {{ path = "../' + package + '" }}\n'
    )
    (project / "pyproject.toml").write_text(project_config.format(version="0"))
    run("uv", "lock", "--offline", cwd=project)
    (project / "check.py").write_text("from fixture_dependency import value\nallowed: str = value\n")
    commit(source)
    options = (
        "uv",
        "run",
        "--script",
        str(ROOT / "stock/containers.py"),
        "--source",
        str(source),
        "--cache",
        str(tmp_path / "cache"),
        "--consumer-config",
        ".mega-linter.yml",
        "--pyright-project",
        "project",
        "--linter",
        "PYTHON_PYRIGHT",
    )
    good = run(*options, "--reports", str(tmp_path / "good"), check=False)
    assert good.returncode == 0, good.stderr[-10000:]
    assert not (project / ".venv").exists()
    (project / "check.py").write_text("value = missing\n")
    base = commit(source)
    (project / "pyproject.toml").write_text(project_config.format(version="1"))
    run("uv", "lock", "--offline", cwd=project)
    lock_change = commit(source)
    reports = tmp_path / "changed-dependencies"
    bad = run(*options, "--reports", str(reports), "--base", base, check=False)
    assert bad.returncode == 1, bad.stderr[-10000:]
    report = json.loads((reports / "python_pyright/mega-linter-report.json").read_text())
    (linter,) = report["active_linters"]
    assert linter["final_config_file"] == "/tmp/lint/rules/types.json"
    assert linter["number_errors"] == 1
    assert "reportUndefinedVariable" in linter["stdout"]

    config = rules / "types.json"
    contents = json.loads(config.read_text())
    config.write_text(json.dumps({**contents, "reportUndefinedVariable": "none"}))
    commit(source)
    reports = tmp_path / "changed-policy"
    fixed = run(*options, "--reports", str(reports), "--base", lock_change, check=False)
    assert fixed.returncode == 0, fixed.stderr[-10000:]
    assert (reports / "python_pyright/mega-linter-report.json").is_file()
    assert not (project / ".venv").exists()


@pytest.mark.skipif(os.environ.get("STOCK_RENOVATE") != "true", reason="Run Renovate on the CI host with Node")
def test_stock_renovate(tmp_path):
    route = tmp_path / ".github/workflows"
    route.mkdir(parents=True)
    shutil.copytree(ROOT / "stock", tmp_path / "stock", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(ROOT / ".github/workflows/stock-lint.yml", route / "stock-lint.yml")
    shutil.copyfile(FIXTURE / "consumer.yml.fixture", route / "consumer.yml")
    shutil.copyfile(ROOT / "renovate.json", tmp_path / "renovate.json")
    run("git", "init", "--quiet", cwd=tmp_path)
    commit(tmp_path)
    run("renovate-config-validator", "--strict", "renovate.json", cwd=tmp_path)
    environment = {**os.environ, "LOG_FORMAT": "json", "LOG_LEVEL": "debug"}
    dry_run = run("renovate", "--platform=local", "--dry-run=extract", cwd=tmp_path, env=environment)
    logs = [json.loads(line) for line in dry_run.stdout.splitlines() if line.startswith("{")]
    packages = next(row["packageFiles"] for row in logs if row["msg"] == "Extracted dependencies")
    dependencies = sorted(
        {
            (manager, dep["depName"])
            for manager, files in packages.items()
            for file in files
            for dep in file["deps"]
            if dep.get("depName") and dep.get("currentValue")
        }
    )
    assert list(map(list, dependencies)) == EXPECTED["dependencies"], json.dumps(dependencies, indent=2)
