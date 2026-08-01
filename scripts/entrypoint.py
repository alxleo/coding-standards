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
REQUIRED_LOCAL_CONFIGS_KEY = "CODING_STANDARDS_REQUIRED_LOCAL_CONFIGS"

app = typer.Typer(
    name="coding-standards",
    help="Centralized linting image. Detects your stack, runs the right checks.",
    add_completion=False,
    invoke_without_command=True,
)


def _workspace() -> Path:
    return Path(os.environ.get("DEFAULT_WORKSPACE", "/tmp/lint"))


def _local_rules_directory(rules_path: str, workspace: Path) -> Path:
    rules_directory = (workspace / rules_path).resolve()
    if rules_directory.is_relative_to(workspace.resolve()) and rules_directory.is_dir():
        return rules_directory
    message = f"LINTER_RULES_PATH should be a workspace directory ({rules_path})"
    raise ValueError(message)


def _select_matching_consumer_configs(
    merged: dict[str, object], overrides: dict[str, object], rules_path: str, rules_directory: Path
) -> None:
    for key, value in tuple(merged.items()):
        if not (key.endswith("_CONFIG_FILE") and isinstance(value, str)):
            continue
        config_path = Path(value)
        if config_path.is_absolute() or len(config_path.parts) != 1:
            continue
        if (rules_directory / config_path).is_file():
            rules_key = f"{key.removesuffix('_CONFIG_FILE')}_RULES_PATH"
            if rules_key not in overrides:
                # MegaLinter searches the workspace root before RULES_PATH. Use
                # the explicit workspace-relative filename so the canonical
                # directory wins even during a migration with stale root files.
                merged[key] = str(Path(rules_path) / config_path)


def _warn_for_missing_overrides(overrides: dict[str, object], workspace: Path, rules_directory: Path) -> None:
    for key, value in overrides.items():
        if not (key.endswith("_CONFIG_FILE") and isinstance(value, str)):
            continue
        config_path = Path(value)
        if config_path.is_absolute():
            continue
        if not (workspace / config_path).is_file() and not (rules_directory / config_path).is_file():
            typer.echo(f"Warning: {key} override points to missing file: {value}", err=True)


def _validate_required_local_configs(
    merged: dict[str, object], required: object, workspace: Path, rules_directory: Path
) -> None:
    if required is None:
        return
    if not isinstance(required, list) or not all(isinstance(key, str) for key in required):
        message = f"{REQUIRED_LOCAL_CONFIGS_KEY} must be a list of _CONFIG_FILE keys"
        raise ValueError(message)

    errors: list[str] = []
    for key in required:
        if not key.endswith("_CONFIG_FILE"):
            errors.append(f"{key}: expected a _CONFIG_FILE key")
            continue
        value = merged.get(key)
        if not isinstance(value, str):
            errors.append(f"{key}: no effective config is declared")
            continue
        resolved = (workspace / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
        if not resolved.is_relative_to(rules_directory) or not resolved.is_file():
            errors.append(f"{key}: {value} is not a file under {rules_directory.relative_to(workspace)}")

    if errors:
        message = "Required local linter configs did not resolve:\n- " + "\n- ".join(errors)
        raise ValueError(message)


def _apply_consumer_rules_directory(merged: dict[str, object], overrides: dict[str, object], workspace: Path) -> None:
    """Overlay a consumer LINTER_RULES_PATH without hiding baked configs.

    MegaLinter treats LINTER_RULES_PATH as a replacement.  The coding-standards
    image instead keeps its baked directory as the fallback and selects each
    matching consumer config by its explicit workspace-relative path. This also
    avoids MegaLinter v9.6's root-first search order and absolute-path
    activation bug.
    """
    required = overrides.pop(REQUIRED_LOCAL_CONFIGS_KEY, None)
    merged.pop(REQUIRED_LOCAL_CONFIGS_KEY, None)
    rules_path = overrides.pop("LINTER_RULES_PATH", None)
    if rules_path is None:
        if required is not None:
            message = f"{REQUIRED_LOCAL_CONFIGS_KEY} requires LINTER_RULES_PATH"
            raise ValueError(message)
        return
    if not isinstance(rules_path, str) or not rules_path.strip():
        message = "LINTER_RULES_PATH must be a non-empty directory path"
        raise ValueError(message)
    if rules_path.startswith("http") or Path(rules_path).is_absolute():
        merged["LINTER_RULES_PATH"] = rules_path
        return

    rules_directory = _local_rules_directory(rules_path, workspace)
    _select_matching_consumer_configs(merged, overrides, rules_path, rules_directory)
    _warn_for_missing_overrides(overrides, workspace, rules_directory)
    _validate_required_local_configs(merged, required, workspace, rules_directory)


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

    # Git credential helper for GitHub API + git protocol.
    # Tools like zizmor use git-upload-pack (git protocol) to verify action
    # pins, which doesn't use GITHUB_TOKEN env var. Configure git to use
    # the token for all github.com HTTPS operations.
    gh_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if gh_token:
        # Store credentials via git credential store so git-upload-pack
        # (used by zizmor for action pin verification) authenticates.
        cred_path = Path("/tmp/.git-credentials")
        fd = os.open(cred_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(f"https://x-access-token:{gh_token}@github.com\n")
        subprocess.run(
            ["git", "config", "--global", "credential.helper", f"store --file={cred_path}"],
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
            consumer_rules_path = overrides.pop("LINTER_RULES_PATH", None)
            baked.update(overrides)
            if consumer_rules_path is not None:
                overrides["LINTER_RULES_PATH"] = consumer_rules_path
            _apply_consumer_rules_directory(baked, overrides, workspace)
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
    with tempfile.NamedTemporaryFile(suffix=".json", prefix="repo-manifest-", delete=False) as f:
        manifest = Path(f.name)
    try:
        subprocess.run(
            ["python3", str(SCRIPTS / "generate_repo_manifest.py"), str(workspace), str(manifest)],
            check=True,
        )
        subprocess.run(
            [
                "conftest",
                "test",
                str(manifest),
                "--all-namespaces",
                "--no-color",
                "-p",
                "/opt/coding-standards/policies/repo-standards/",
            ],
            check=True,
        )
    finally:
        manifest.unlink(missing_ok=True)


@app.command()
def recommend() -> None:
    """Show recommended checks for this repo (JSON output)."""
    workspace = _workspace()
    subprocess.run(
        ["python3", str(SCRIPTS / "recommend.py"), str(workspace)],
        check=True,
    )


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def catalog(ctx: typer.Context) -> None:
    """Show full catalog of checks. Use --rules for per-tool rule details."""
    subprocess.run(
        ["python3", str(SCRIPTS / "show_catalog.py"), *ctx.args],
        check=True,
    )


@app.command()
def warnings() -> None:
    """Show warnings from last run (grouped by linter)."""
    os.chdir(_workspace())
    subprocess.run(["python3", str(SCRIPTS / "show_warnings.py")], check=True)


@app.command(name="show-config", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def show_config(ctx: typer.Context) -> None:
    """Show which config file each linter uses + local overrides."""
    os.chdir(_workspace())
    subprocess.run(
        [
            "python3",
            str(SCRIPTS / "show_config.py"),
            ".",
            "--mega-linter-yml",
            os.environ.get("MEGALINTER_CONFIG", str(BAKED_CONFIG)),
            *ctx.args,
        ],
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
