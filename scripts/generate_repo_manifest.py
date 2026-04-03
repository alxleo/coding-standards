#!/usr/bin/env python3
"""Generate repo-manifest.json for conftest repo-standards validation.

Scans the workspace and outputs a JSON manifest of:
- File existence (configs, lockfiles, tooling setup)
- Directory presence (tests, secrets, workflows)
- Content counts (Python/JS/shell files by language)
- Dependency checks (pytest-randomly, eslint-plugin-jest, etc.)
- CI configuration fields (EXTENDS URL, action pins, fetch-depth)

The manifest is consumed by policies/repo-standards/*.rego via conftest.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

EXCLUDES = {
    ".git",
    ".worktrees",
    "__pycache__",
    ".ruff_cache",
    "venv",
    ".venv",
    "node_modules",
    ".terraform",
    "megalinter-reports",
    ".mypy_cache",
    "coverage",
    ".nyc_output",
    ".next",
    ".nuxt",
    "dist",
    "build",
    "ansible/collections",
    ".claude",
}

# Split excludes: simple names match path parts, slashed entries match prefixes
_EXCLUDE_PARTS = {e for e in EXCLUDES if "/" not in e}
_EXCLUDE_PREFIXES = tuple(e.rstrip("/") for e in EXCLUDES if "/" in e)


def _is_excluded(rel: Path) -> bool:
    """Return True if the given path (relative to root) should be excluded."""
    if any(part in _EXCLUDE_PARTS for part in rel.parts):
        return True
    rel_str = rel.as_posix()
    return any(
        rel_str == prefix or rel_str.startswith(prefix + "/")  # nosemgrep: coding-standards.python-silent-fallback-or
        for prefix in _EXCLUDE_PREFIXES
    )


def count_files(root: Path, suffix: str) -> int:
    return sum(1 for f in root.rglob(f"*{suffix}") if not _is_excluded(f.relative_to(root)))


def _load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file using stdlib tomllib (requires Python 3.11+)."""
    import tomllib

    with Path.open(path, "rb") as f:
        return tomllib.load(f)


def check_pyproject_dep(root: Path, dep_name: str) -> bool:
    """Check if dep_name appears in any dependency list in pyproject.toml.

    Parses TOML to inspect actual dependency arrays rather than substring
    matching, which could false-positive on description text or comments.
    """
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return False
    try:
        data = _load_toml(pyproject)
    except (OSError, ValueError):
        return False
    # Collect all dependency lists: [project.dependencies],
    # [project.optional-dependencies.*], [dependency-groups.*]
    dep_lists: list[list[str]] = []
    project = data.get("project", {})
    dep_lists.append(project.get("dependencies", []))
    # optional-dependencies may be absent; default to empty dict for .values()
    dep_lists.extend(
        (project.get("optional-dependencies") or {}).values()  # nosemgrep: coding-standards.python-silent-fallback-or
    )
    dep_lists.extend(
        [e for e in group if isinstance(e, str)]
        # dependency-groups may be absent; default to empty dict for .values()
        for group in (  # nosemgrep: coding-standards.python-silent-fallback-or
            data.get("dependency-groups") or {}
        ).values()
    )
    # Check each dependency spec for an exact package name match
    dep_re = re.compile(rf"^{re.escape(dep_name)}(\s*[\[><=!~;@]|$)", re.IGNORECASE)
    return any(dep_re.match(dep) for deps in dep_lists for dep in deps)


def _count_large_shell(root: Path, threshold: int, skip_paths: set[str] | None = None) -> int:
    """Count shell scripts exceeding threshold lines, skipping acknowledged paths."""
    count = 0
    for f in root.rglob("*.sh"):
        rel = f.relative_to(root)
        if _is_excluded(rel):
            continue
        if skip_paths and rel.as_posix() in skip_paths:
            continue
        try:
            lines = len(f.read_text(errors="replace").splitlines())
            if lines > threshold:
                count += 1
        except OSError:
            pass
    return count


def _count_large_ci_run_blocks(root: Path, threshold: int, skip_paths: set[str] | None = None) -> int:
    """Count CI workflow run: blocks exceeding threshold lines, skipping acknowledged paths."""
    count = 0
    for wf in _workflow_files(root):
        rel = wf.relative_to(root)
        if skip_paths and rel.as_posix() in skip_paths:
            continue
        try:
            data = yaml.safe_load(wf.read_text(errors="replace"))
            if not isinstance(data, dict):
                continue
            jobs = data.get("jobs")  # YAML `jobs:` with no value → None
            if not isinstance(jobs, dict):
                continue
            for job in jobs.values():
                if not isinstance(job, dict):
                    continue
                steps = job.get("steps")
                if not isinstance(steps, list):
                    continue
                for step in steps:
                    if not isinstance(step, dict):
                        continue
                    run_block = step.get("run", "")
                    if isinstance(run_block, str) and len(run_block.splitlines()) > threshold:
                        count += 1
        except (yaml.YAMLError, OSError):
            pass
    return count


def _count_large_justfile_recipes(root: Path, threshold: int) -> int:
    """Count justfile recipes exceeding threshold lines."""
    justfile = root / "justfile"
    if not justfile.exists():
        # Also check Justfile (capital J)
        justfile = root / "Justfile"
        if not justfile.exists():
            return 0
    count = 0
    body_lines = 0
    in_recipe = False
    try:
        for line in justfile.read_text(errors="replace").splitlines():
            # Recipe body lines are indented (spaces or tabs)
            if in_recipe and (line.startswith((" ", "\t"))):
                body_lines += 1
            else:
                # End of previous recipe — check threshold
                if in_recipe and body_lines > threshold:
                    count += 1
                # New recipe starts with unindented name containing ':'
                # Skip comments, blank lines, variable assignments (`:=`)
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and ":" in stripped and ":=" not in stripped:
                    in_recipe = True
                    body_lines = 0
                else:
                    in_recipe = False
        # Final recipe
        if in_recipe and body_lines > threshold:
            count += 1
    except OSError:
        pass
    return count


def _has_toml_section(path: Path, *keys: str) -> bool:
    """Check if a nested section exists in a TOML file."""
    if not path.exists():
        return False
    try:
        data = _load_toml(path)
        for key in keys:
            # Guard: TOML values may be non-dict at any nesting level
            if not isinstance(data, dict) or key not in data:  # nosemgrep: coding-standards.python-silent-fallback-or
                return False
            data = data[key]
        return True
    except (OSError, ValueError):
        return False


def check_package_json_dep(root: Path, dep_name: str) -> bool:
    pkg = root / "package.json"
    if not pkg.exists():
        return False
    text = pkg.read_text(errors="replace")
    return dep_name in text


def _has_any_dep(root: Path, pyproject: tuple[str, ...] = (), pkg: tuple[str, ...] = ()) -> bool:
    """Check if any of the given deps exist in pyproject.toml or package.json."""
    checks = [check_pyproject_dep(root, d) for d in pyproject]
    checks.extend(check_package_json_dep(root, d) for d in pkg)
    return any(checks)


def _max_blast_radius(root: Path) -> int:
    """Highest blast radius (filename reference count) in the repo."""
    try:
        from blast_radius import compute_blast_radius

        data = compute_blast_radius(root)
        return max((r["blast_radius"] for r in data), default=0)
    except (ImportError, OSError, ValueError):
        return 0


def _max_naming_entropy(root: Path) -> float:
    """Highest naming convention entropy across directories."""
    try:
        from blast_radius import compute_naming_entropy

        data = compute_naming_entropy(root)
        return max((r["entropy"] for r in data), default=0.0)
    except (ImportError, OSError, ValueError):
        return 0.0


def _extract_pre_commit_hooks(root: Path) -> list[str]:
    """Extract hook IDs from .pre-commit-config.yaml."""
    pc = root / ".pre-commit-config.yaml"
    if not pc.exists():
        return []
    try:
        data = yaml.safe_load(pc.read_text(errors="replace"))
    except (yaml.YAMLError, OSError):
        return []
    if not isinstance(data, dict):
        return []
    hooks = []
    for repo in data.get("repos", []):
        for hook in repo.get("hooks", []):
            hook_id = hook.get("id", "")
            if hook_id:
                hooks.append(hook_id)
    return sorted(hooks)


def extract_extends_url(root: Path) -> str | None:
    ml = root / ".mega-linter.yml"
    if not ml.exists():
        return None
    text = ml.read_text(errors="replace")
    lines = text.splitlines()
    url_re = re.compile(r"https?://\S+")

    for i, line in enumerate(lines):
        if re.match(r"\s*EXTENDS\s*:", line):
            # Inline form: EXTENDS: https://... or EXTENDS: [https://...]
            inline_match = url_re.search(line)
            if inline_match:
                return inline_match.group(0)
            # Block form: scan following lines, skipping blanks/comments
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                # Skip blank lines and YAML comments between EXTENDS: and list items
                if not next_line or next_line.startswith("#"):  # nosemgrep: coding-standards.python-silent-fallback-or
                    j += 1
                    continue
                if next_line.startswith("-"):
                    list_match = url_re.search(next_line)
                    if list_match:
                        return list_match.group(0)
                break
    return None


def check_gitignore_covers(root: Path, pattern: str) -> bool:
    gi = root / ".gitignore"
    if not gi.exists():
        return False
    return pattern in gi.read_text(errors="replace")


def _workflow_files(root: Path):
    """Yield all workflow files (.yml and .yaml) from GitHub and Gitea dirs."""
    for wf_dir in [root / ".github/workflows", root / ".gitea/workflows"]:
        if wf_dir.is_dir():
            yield from wf_dir.glob("*.yml")
            yield from wf_dir.glob("*.yaml")


def check_workflow_field(root: Path, pattern: str) -> bool:
    """Check if any workflow file contains a pattern."""
    return any(pattern in wf.read_text(errors="replace") for wf in _workflow_files(root))


def check_ci_delegates_to_runner(root: Path) -> bool:
    """Check that CI run: steps delegate to a task runner, not inline linting.

    CI should call `just check` or `make check`, not `uvx ruff ...` or
    `pytest ...` directly. Inline linting in CI drifts from local dev.
    """
    inline_linters = re.compile(
        r"^\s*(?:run:\s*\|?\s*)?"
        r"(?:uvx |npx |pip |uv run )?"
        r"(?:ruff |semgrep |pytest |pylint |mypy |eslint |prettier )"
    )
    for wf in _workflow_files(root):
        for line in wf.read_text(errors="replace").splitlines():
            if inline_linters.search(line):
                return False
    return True


def check_ci_mixes_schedule(root: Path) -> bool:
    """Check if any workflow mixes schedule triggers with push/PR triggers."""
    for wf in _workflow_files(root):
        text = wf.read_text(errors="replace")
        has_schedule = "schedule:" in text
        has_push_or_pr = "push:" in text or "pull_request:" in text
        if has_schedule and has_push_or_pr:
            return True
    return False


def check_actions_pinned(root: Path) -> bool:
    """Check if all 'uses:' in workflows reference SHA pins (contain @sha)."""
    found_any = False
    for wf in _workflow_files(root):
        for line in wf.read_text(errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith(("- uses:", "uses:")):
                found_any = True
                ref = stripped.split("@")[-1] if "@" in stripped else ""
                # SHA pins are 40 hex chars
                if ref and not re.match(r"[0-9a-f]{40}", ref.split()[0]):
                    return False
    return found_any


def check_run_blocks_have_groups(root: Path) -> bool:
    """Check that multi-line run: blocks use ::group:: markers for log structuring.

    Gitea Actions and gitea-ci parse ::group::/::endgroup:: markers for per-step
    log visibility. Without them, all step output merges into one blob.
    Single-line run: blocks are exempt (too short to benefit).
    """
    for wf in _workflow_files(root):
        try:
            data = yaml.safe_load(wf.read_text(errors="replace"))
        except (yaml.YAMLError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        for job in data.get("jobs", {}).values():
            if not isinstance(job, dict):
                continue
            for step in job.get("steps", []):
                if not isinstance(step, dict):
                    continue
                run_block = step.get("run", "")
                if not isinstance(run_block, str):
                    continue
                # Only check multi-line run blocks (single-line too short to need groups)
                if "\n" in run_block.strip():
                    has_group = "::group::" in run_block
                    has_endgroup = "::endgroup::" in run_block
                    if not (has_group and has_endgroup):
                        return False
    return True


def _get_triggers(data: dict[str | bool, Any]) -> dict[str, Any]:
    """Extract the triggers dict from a parsed workflow, handling YAML `on:` → True.

    YAML spec parses the bare keyword `on:` as boolean True, so the parsed
    dict has {True: {...}} not {"on": {...}}. We check both keys.
    """
    triggers = data.get(True)
    if triggers is None:
        triggers = data.get("on")
    if triggers is None:
        return {}
    if isinstance(triggers, str):
        return {triggers: None}
    if isinstance(triggers, list):
        return dict.fromkeys(triggers)
    if isinstance(triggers, dict):
        return triggers
    return {}


def _has_push_trigger(data: dict[str | bool, Any]) -> bool:
    """Check if a parsed workflow has a push trigger (any form)."""
    return "push" in _get_triggers(data)


def check_push_trigger_all_branches(root: Path) -> bool:
    """Check that push triggers don't filter by branch.

    The CI-on-every-commit model (Gitea) needs all branches to trigger CI.
    Both `branches` and `branches-ignore` are branch restrictions.
    """
    for wf in _workflow_files(root):
        try:
            data = yaml.safe_load(wf.read_text(errors="replace"))
        except (yaml.YAMLError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        triggers = _get_triggers(data)
        push = triggers.get("push")
        if isinstance(push, dict) and ("branches" in push or "branches-ignore" in push):
            return False
    return True


def check_github_token_workaround(root: Path) -> bool:
    """Check that push-triggered workflows using github.com actions have the fix.

    Gitea overrides GITHUB_TOKEN with a Gitea-scoped token. Workflows that run
    on Gitea (push-triggered) and call github.com APIs need the workaround:
        echo "GITHUB_TOKEN=$REAL_GITHUB_TOKEN" >> "$GITHUB_ENV"

    Returns True if no push-triggered workflows use github.com actions,
    or if those that do have the workaround step.
    Skips schedule/dispatch-only workflows (GitHub-only, no Gitea).
    """
    for wf in _workflow_files(root):
        try:
            data = yaml.safe_load(wf.read_text(errors="replace"))
        except (yaml.YAMLError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        if not _has_push_trigger(data):
            continue
        text = wf.read_text(errors="replace")
        # Any uses: with owner/repo@ref pattern is a GitHub-hosted action.
        # Exclude local actions (./) and docker:// references.
        has_github_actions = any(
            "uses:" in line and "./" not in line.split("uses:")[-1] and "docker://" not in line.split("uses:")[-1]
            for line in text.splitlines()
            if "uses:" in line
        )
        if has_github_actions and "REAL_GITHUB_TOKEN" not in text:
            return False
    return True


def _has_health_route(root: Path) -> bool:
    """Check if any source file defines a health endpoint."""
    patterns = ["/health", "/healthz", "/ready", "/readyz"]
    for f in root.rglob("*"):
        if any((f.is_dir(), _is_excluded(f.relative_to(root)))):
            continue
        if f.suffix not in (".py", ".js", ".ts", ".tsx"):
            continue
        try:
            text = f.read_text(errors="replace")
            if any(p in text for p in patterns):
                return True
        except OSError:
            pass
    return False


def load_acknowledged(root: Path) -> dict[str, Any]:
    """Load .repo-standards.yml acknowledged entries.

    Values can be:
      - string: permanent ("not applicable — no boundaries")
      - {reason, expires, tracking}: temporary — stripped when expired
      - list of {path, reason}: per-file exceptions
    """
    from datetime import UTC, date, datetime

    import yaml

    rs = root / ".repo-standards.yml"
    if not rs.exists():
        return {}
    try:
        with rs.open() as f:
            data = yaml.safe_load(f) or {}  # nosemgrep: coding-standards.python-silent-fallback-or
        ack = data.get("acknowledged", {}) or {}  # nosemgrep: coding-standards.python-silent-fallback-or

        # Strip expired temporary acknowledgments
        today = datetime.now(tz=UTC).date()
        result: dict[str, Any] = {}
        for key, value in ack.items():
            if isinstance(value, dict) and "expires" in value:
                try:
                    expires = date.fromisoformat(str(value["expires"]))
                    if expires < today:
                        print(f"repo-standards: acknowledged '{key}' expired on {expires}")
                        continue
                except (ValueError, TypeError):
                    pass
            result[key] = value
        return result
    except (OSError, ValueError, yaml.YAMLError):
        return {}


def _acknowledged_paths(acknowledged: dict[str, Any], check_id: str) -> set[str]:
    """Extract acknowledged file paths for a check (per-file exceptions)."""
    value = acknowledged.get(check_id)
    if not isinstance(value, list):
        return set()
    return {entry["path"] for entry in value if isinstance(entry, dict) and "path" in entry}


def _count_suppressions(root: Path) -> dict[str, int]:
    """Count inline suppression comments across the codebase."""
    patterns = {
        "noqa": r"#\s*noqa",
        "type_ignore": r"#\s*type:\s*ignore",
        "nosemgrep": r"#\s*nosemgrep",
        "shellcheck_disable": r"#\s*shellcheck\s+disable",
    }
    counts: dict[str, int] = dict.fromkeys(patterns, 0)
    for f in root.rglob("*"):
        # Skip directories and excluded paths (vendor, build, etc.)
        if any((f.is_dir(), _is_excluded(f.relative_to(root)))):
            continue
        if f.suffix not in (".py", ".sh", ".bash", ".js", ".ts", ".tsx", ".jsx"):
            continue
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        for name, pattern in patterns.items():
            counts[name] += len(re.findall(pattern, text))
    # File-level suppressions
    counts["trivyignore"] = (
        len((root / ".trivyignore").read_text().splitlines()) if (root / ".trivyignore").exists() else 0
    )
    counts["gitleaksignore"] = (
        len((root / ".gitleaksignore").read_text().splitlines()) if (root / ".gitleaksignore").exists() else 0
    )
    counts["total"] = sum(counts.values())
    return counts


def generate(root: Path) -> dict[str, Any]:
    from manifest_schema import Manifest

    ack = load_acknowledged(root)
    data = {
        "files": {
            "pyrightconfig": (root / "pyrightconfig.json").exists(),
            "ruff": (root / "ruff.toml").exists(),
            "gitleaks": (root / ".gitleaks.toml").exists(),
            "sops": (root / ".sops.yaml").exists(),
            "trivy": (root / "trivy.yaml").exists(),
            "mega_linter": (root / ".mega-linter.yml").exists(),
            "mega_linter_extends_url": extract_extends_url(root),
            "conftest_toml": (root / "conftest.toml").exists(),
            "editorconfig": (root / ".editorconfig").exists(),
            "tsconfig": (root / "tsconfig.json").exists(),
            "eslint_config": any(
                (root / f).exists()
                for f in [
                    "eslint.config.js",
                    "eslint.config.mjs",
                    ".eslintrc.js",
                    ".eslintrc.json",
                    ".eslintrc.yml",
                ]
            ),
            "pre_commit_config": (root / ".pre-commit-config.yaml").exists(),
            "commitlint_config": any(
                (root / f).exists()
                for f in [
                    "commitlint.config.js",
                    "commitlint.config.mjs",
                    "commitlint.config.cjs",
                    ".commitlintrc.yml",
                    ".commitlintrc.json",
                ]
            ),
            "gitignore": (root / ".gitignore").exists(),
            "gitignore_covers_decrypted": check_gitignore_covers(root, ".decrypted"),
            "ci_json": (root / ".ci.json").exists(),
            "renovate": any((root / f).exists() for f in ("renovate.json", ".renovaterc.json")),
            "nvmrc": (root / ".nvmrc").exists(),
            "envrc": (root / ".envrc").exists(),
            "makefile": any((root / f).exists() for f in ("Makefile", "justfile")),
            "env_example": (root / ".env.example").exists(),
            "gitignore_covers_spikes": check_gitignore_covers(root, "spikes"),
        },
        "directories": {
            "tests": any((root / d).is_dir() for d in ("tests", "test")),
            "secrets": (root / "secrets").is_dir(),
            "decrypted": (root / ".decrypted").is_dir(),
            "github_workflows": (root / ".github/workflows").is_dir(),
            "gitea_workflows": (root / ".gitea/workflows").is_dir(),
        },
        "content": {
            "python_files": count_files(root, ".py"),
            "typescript_files": count_files(root, ".ts") + count_files(root, ".tsx"),
            "javascript_files": count_files(root, ".js") + count_files(root, ".jsx"),
            "shell_files": count_files(root, ".sh"),
            "compose_files": sum(
                1
                for p in [
                    "docker-compose*.yml",
                    "docker-compose*.yaml",
                    "compose*.yml",
                    "compose*.yaml",
                ]
                for f in root.rglob(p)
                if not _is_excluded(f.relative_to(root))
            ),
            "shell_scripts_over_30_lines": _count_large_shell(
                root, 30, _acknowledged_paths(ack, "large_shell_scripts")
            ),
            "justfile_recipes_over_10_lines": _count_large_justfile_recipes(root, 10),
            "python_files_with_hyphens": sum(
                1 for f in root.rglob("*.py") if not _is_excluded(f.relative_to(root)) and "-" in f.stem
            ),
            "dockerfile_files": sum(1 for _ in root.rglob("Dockerfile*") if not _is_excluded(_.relative_to(root))),
            "pre_commit_hooks": _extract_pre_commit_hooks(root),
            "max_blast_radius": _max_blast_radius(root),
            "max_naming_entropy": _max_naming_entropy(root),
        },
        "dependencies": {
            "pytest_randomly": check_pyproject_dep(root, "pytest-randomly"),
            "test_deps_defined": check_pyproject_dep(root, "pytest"),
            "eslint_plugin_jest": check_package_json_dep(root, "eslint-plugin-jest"),
            "zod": check_package_json_dep(root, "zod"),
            "pydantic": check_pyproject_dep(root, "pydantic"),
            "import_linter": check_pyproject_dep(root, "import-linter"),
            "import_linter_configured": _has_toml_section(root / "pyproject.toml", "tool", "importlinter"),
            "hypothesis": check_pyproject_dep(root, "hypothesis"),
            "stryker": check_package_json_dep(root, "@stryker-mutator/core"),
            "i18n_framework": _has_any_dep(root, pkg=("i18next", "react-intl", "next-intl")),
            "structured_logging_js": _has_any_dep(root, pkg=("pino", "winston", "bunyan")),
            "structured_logging_py": _has_any_dep(root, pyproject=("structlog", "python-json-logger")),
            "opentelemetry": _has_any_dep(root, pyproject=("opentelemetry-sdk",), pkg=("@opentelemetry/sdk-node",)),
        },
        "ci": {
            "workflow_uses_composite_action": check_workflow_field(root, "coding-standards/docker-action"),
            "workflow_fetch_depth_zero": check_workflow_field(root, "fetch-depth: 0"),
            "workflow_persist_credentials_false": check_workflow_field(root, "persist-credentials: false"),
            "workflow_actions_sha_pinned": check_actions_pinned(root),
            "ci_delegates_to_runner": check_ci_delegates_to_runner(root),
            "ci_mixes_schedule_and_push": check_ci_mixes_schedule(root),
            "has_sha_pins": check_workflow_field(root, "@") and check_actions_pinned(root),
            "ci_run_blocks_over_10_lines": _count_large_ci_run_blocks(
                root, 10, _acknowledged_paths(ack, "large_ci_run_blocks")
            ),
            "run_blocks_have_groups": check_run_blocks_have_groups(root),
            "push_trigger_all_branches": check_push_trigger_all_branches(root),
            "github_token_workaround": check_github_token_workaround(root),
            "has_scheduled_dockle": check_workflow_field(root, "dockle"),
        },
        "observability": {
            "is_service": any(
                (
                    _has_any_dep(
                        root,
                        pyproject=("fastapi", "flask", "django"),
                        pkg=("express", "hono", "fastify", "next"),
                    ),
                    (root / "Dockerfile").exists(),
                )
            ),
            "has_health_route": _has_health_route(root),
            "has_metrics": _has_any_dep(root, pyproject=("prometheus-client",), pkg=("prom-client",)),
            "has_error_tracking": _has_any_dep(root, pyproject=("sentry-sdk",), pkg=("@sentry/node",)),
            "has_tracing": _has_any_dep(root, pyproject=("opentelemetry-sdk",), pkg=("@opentelemetry/sdk-node",)),
        },
        "acknowledged": ack,
        "suppressions": _count_suppressions(root),
    }
    # Validate against typed schema — catches wrong field names/types at generation time
    return Manifest(**data).model_dump()


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    manifest = generate(root)
    output = root / "repo-manifest.json"
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    lang_keys = ("python_files", "typescript_files", "javascript_files", "shell_files")
    source_count = sum(manifest["content"].get(k, 0) for k in lang_keys)
    print(f"repo-manifest.json generated ({source_count} source files scanned)")
