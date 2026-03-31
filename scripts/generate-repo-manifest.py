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

import json
import re
import sys
from pathlib import Path

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
        rel_str == prefix or rel_str.startswith(prefix + "/")
        for prefix in _EXCLUDE_PREFIXES
    )


def count_files(root: Path, suffix: str) -> int:
    return sum(
        1 for f in root.rglob(f"*{suffix}") if not _is_excluded(f.relative_to(root))
    )


def _load_toml(path: Path) -> dict:
    """Load a TOML file, using stdlib tomllib (3.11+) or tomli fallback."""
    try:
        import tomllib as _toml
    except ModuleNotFoundError:
        import tomli as _toml
    with open(path, "rb") as f:
        return _toml.load(f)


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
    except Exception:
        return False
    # Collect all dependency lists: [project.dependencies], [project.optional-dependencies.*],
    # [dependency-groups.*]
    dep_lists: list[list[str]] = []
    project = data.get("project", {})
    dep_lists.append(project.get("dependencies", []))
    for group in (project.get("optional-dependencies") or {}).values():
        dep_lists.append(group)
    for group in (data.get("dependency-groups") or {}).values():
        dep_lists.append([e for e in group if isinstance(e, str)])
    # Check each dependency spec for an exact package name match
    dep_re = re.compile(rf"^{re.escape(dep_name)}(\s*[\[><=!~;@]|$)", re.IGNORECASE)
    return any(dep_re.match(dep) for deps in dep_lists for dep in deps)


def check_package_json_dep(root: Path, dep_name: str) -> bool:
    pkg = root / "package.json"
    if not pkg.exists():
        return False
    text = pkg.read_text(errors="replace")
    return dep_name in text


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
                if not next_line or next_line.startswith("#"):
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
    for wf in _workflow_files(root):
        if pattern in wf.read_text(errors="replace"):
            return True
    return False


def check_actions_pinned(root: Path) -> bool:
    """Check if all 'uses:' in workflows reference SHA pins (contain @sha)."""
    found_any = False
    for wf in _workflow_files(root):
        for line in wf.read_text(errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("- uses:") or stripped.startswith("uses:"):
                found_any = True
                ref = stripped.split("@")[-1] if "@" in stripped else ""
                # SHA pins are 40 hex chars
                if ref and not re.match(r"[0-9a-f]{40}", ref.split()[0]):
                    return False
    return found_any


def load_acknowledged(root: Path) -> dict[str, str]:
    """Load .repo-standards.yml acknowledged entries."""
    rs = root / ".repo-standards.yml"
    if not rs.exists():
        return {}
    try:
        import yaml

        with open(rs) as f:
            data = yaml.safe_load(f) or {}
        return data.get("acknowledged", {}) or {}
    except Exception:
        return {}


def generate(root: Path) -> dict:
    return {
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
                    "commitlint.config.baseline.mjs",
                    ".commitlintrc.yml",
                    ".commitlintrc.json",
                ]
            ),
            "gitignore": (root / ".gitignore").exists(),
            "gitignore_covers_decrypted": check_gitignore_covers(root, ".decrypted"),
            "ci_json": (root / ".ci.json").exists(),
            "renovate": (root / "renovate.json").exists()
            or (root / ".renovaterc.json").exists(),
        },
        "directories": {
            "tests": (root / "tests").is_dir() or (root / "test").is_dir(),
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
                len(list(root.glob(p)))
                for p in [
                    "docker-compose*.yml",
                    "docker-compose*.yaml",
                    "compose*.yml",
                    "compose*.yaml",
                ]
            ),
            "dockerfile_files": sum(
                1
                for _ in root.rglob("Dockerfile*")
                if not _is_excluded(_.relative_to(root))
            ),
        },
        "dependencies": {
            "pytest_randomly": check_pyproject_dep(root, "pytest-randomly"),
            "test_deps_defined": check_pyproject_dep(root, "pytest"),
            "eslint_plugin_jest": check_package_json_dep(root, "eslint-plugin-jest"),
        },
        "ci": {
            "workflow_uses_composite_action": check_workflow_field(
                root, "coding-standards/docker-action"
            ),
            "workflow_fetch_depth_zero": check_workflow_field(root, "fetch-depth: 0"),
            "workflow_persist_credentials_false": check_workflow_field(
                root, "persist-credentials: false"
            ),
            "workflow_actions_sha_pinned": check_actions_pinned(root),
            "has_sha_pins": check_workflow_field(root, "@")
            and check_actions_pinned(root),
        },
        "acknowledged": load_acknowledged(root),
    }


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    manifest = generate(root)
    output = root / "repo-manifest.json"
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        f"repo-manifest.json generated ({sum(manifest['content'].values())} source files scanned)"
    )
