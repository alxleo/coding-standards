#!/usr/bin/env python3
"""coding-standards entrypoint — routes commands to MegaLinter or built-in tools.

Usage:
    docker run ... ghcr.io/alxleo/coding-standards:latest              # full lint
    docker run ... ghcr.io/alxleo/coding-standards:latest lint ruff     # single linter
    docker run ... ghcr.io/alxleo/coding-standards:latest fix           # auto-fix
    docker run ... ghcr.io/alxleo/coding-standards:latest recommend     # what to enable
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

import typer
import yaml

SCRIPTS = Path("/opt/coding-standards/scripts")
BAKED_CONFIG = Path("/opt/coding-standards/.mega-linter-default.yml")
EXTENDS_URL = "https://raw.githubusercontent.com/alxleo/coding-standards/main/.mega-linter-default.yml"

app = typer.Typer(
    name="coding-standards",
    help="Centralized linting image. Detects your stack, runs the right checks.",
    add_completion=False,
    invoke_without_command=True,
)


def _workspace() -> Path:
    return Path(os.environ.get("DEFAULT_WORKSPACE", "/tmp/lint"))


def _resolve_config_overrides(overrides: dict, workspace: Path) -> None:
    """Rewrite _CONFIG_FILE overrides to workspace-absolute paths."""
    workspace_resolved = workspace.resolve()
    for key, value in overrides.items():
        if not (key.endswith("_CONFIG_FILE") and isinstance(value, str) and not Path(value).is_absolute()):
            continue
        candidate = (workspace / value).resolve()
        if not candidate.is_relative_to(workspace_resolved):
            continue
        if candidate.is_file():
            overrides[key] = str(candidate)
        else:
            typer.echo(f"Warning: {key} override points to missing file: {candidate}", err=True)


def _setup() -> None:
    """Pre-flight: git safe.directory, config resolution, semgrep discovery."""
    workspace = _workspace()

    # Git safe.directory
    if workspace.is_dir():
        subprocess.run(
            ["git", "config", "--global", "--add", "safe.directory", str(workspace)],
            check=False,
            capture_output=True,
        )

    # Config resolution (zero-config by default).
    # MegaLinter resolves EXTENDS relative to workspace — absolute paths break.
    # Strip EXTENDS, use baked config as MEGALINTER_CONFIG, inject consumer
    # overrides as environment variables.
    consumer_config = workspace / ".mega-linter.yml"
    if not consumer_config.exists():
        os.environ["MEGALINTER_CONFIG"] = str(BAKED_CONFIG)
    elif EXTENDS_URL in consumer_config.read_text():
        content = consumer_config.read_text()
        content = re.sub(
            r"EXTENDS:\s*\n\s*-\s*" + re.escape(EXTENDS_URL) + r"\s*\n?",
            "",
            content,
        )
        # Write a merged config: baked defaults + consumer overrides (without EXTENDS).
        # Can't use env vars for _ARGUMENTS (MegaLinter doesn't parse JSON arrays).
        baked = yaml.safe_load(BAKED_CONFIG.read_text())
        overrides = yaml.safe_load(content) if content.strip() else {}
        if overrides:
            _resolve_config_overrides(overrides, workspace)
            baked.update(overrides)
        with tempfile.NamedTemporaryFile(suffix=".yml", prefix="mega-linter-merged-", delete=False, mode="w") as f:
            yaml.dump(baked, f, default_flow_style=False)
            os.environ["MEGALINTER_CONFIG"] = f.name

    # Auto-discover consumer semgrep rules
    semgrep_dir = workspace / ".semgrep"
    if semgrep_dir.is_dir():
        os.environ["REPOSITORY_SEMGREP_RULESETS"] = (
            f"/rules/security-audit.json,/rules/trailofbits.json,/rules/custom/,{semgrep_dir}/"
        )


def _run_megalinter() -> None:
    """Run MegaLinter and exit with its return code."""
    result = subprocess.run(["python3", "-m", "megalinter.run"], check=False)
    raise SystemExit(result.returncode)


@app.callback()
def main(ctx: typer.Context) -> None:
    """Run pre-flight setup, then dispatch to subcommand or MegaLinter."""
    _setup()
    if ctx.invoked_subcommand is None:
        _run_megalinter()


@app.command()
def lint(linter: str = typer.Argument(None, help="Linter name (e.g. ruff, PYTHON_RUFF)")) -> None:
    """Run full lint suite, or a single linter."""
    if linter:
        os.environ["ENABLE_LINTERS"] = linter.upper()
    _run_megalinter()


@app.command()
def fix() -> None:
    """Auto-fix all fixable issues."""
    os.environ["APPLY_FIXES"] = "all"
    _run_megalinter()


@app.command()
def standards() -> None:
    """Run repo-standards checks only."""
    workspace = _workspace()
    os.chdir(workspace)
    subprocess.run(
        ["python3", str(SCRIPTS / "generate_repo_manifest.py")],
        check=True,
    )
    subprocess.run(
        [
            "conftest",
            "test",
            "repo-manifest.json",
            "--all-namespaces",
            "--no-color",
            "-p",
            "/opt/coding-standards/policies/repo-standards/",
        ],
        check=True,
    )
    Path("repo-manifest.json").unlink(missing_ok=True)


@app.command()
def recommend() -> None:
    """Show recommended checks for this repo (JSON output)."""
    workspace = _workspace()
    subprocess.run(
        ["python3", str(SCRIPTS / "recommend.py"), str(workspace)],
        check=True,
    )


@app.command()
def catalog() -> None:
    """Show full catalog of checks."""
    subprocess.run(["python3", str(SCRIPTS / "show_catalog.py")], check=True)


@app.command()
def warnings() -> None:
    """Show warnings from last run (grouped by linter)."""
    os.chdir(_workspace())
    subprocess.run(["python3", str(SCRIPTS / "show_warnings.py")], check=True)


@app.command(name="show-config")
def show_config() -> None:
    """Show which config file each linter uses + local overrides."""
    os.chdir(_workspace())
    subprocess.run(
        ["python3", str(SCRIPTS / "show_config.py"), ".", "--mega-linter-yml", str(BAKED_CONFIG)],
        check=True,
    )


@app.command(name="blast-radius", context_settings={"allow_extra_args": True, "allow_interspersed_args": False})
def blast_radius(ctx: typer.Context) -> None:
    """Change impact analysis (blast radius, coupling, criticality)."""
    os.chdir(_workspace())
    cmd = ["python3", str(SCRIPTS / "blast_radius.py"), *ctx.args]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    app()
