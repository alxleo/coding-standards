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
    ".git", ".worktrees", "__pycache__", ".ruff_cache", "venv", ".venv",
    "node_modules", ".terraform", "megalinter-reports", ".mypy_cache",
    "coverage", ".nyc_output", ".next", ".nuxt", "dist", "build",
    "ansible/collections", ".claude",
}


def count_files(root: Path, suffix: str) -> int:
    return sum(
        1 for f in root.rglob(f"*{suffix}")
        if not any(part in EXCLUDES for part in f.relative_to(root).parts)
    )


def check_pyproject_dep(root: Path, dep_name: str) -> bool:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return False
    text = pyproject.read_text(errors="replace")
    # Check in any section — dependencies, optional-dependencies, dev
    return dep_name in text


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
    match = re.search(r"EXTENDS:\s*\n\s*-\s*(https?://\S+)", text)
    return match.group(1) if match else None


def check_gitignore_covers(root: Path, pattern: str) -> bool:
    gi = root / ".gitignore"
    if not gi.exists():
        return False
    return pattern in gi.read_text(errors="replace")


def check_workflow_field(root: Path, pattern: str) -> bool:
    """Check if any workflow file contains a pattern."""
    for wf_dir in [root / ".github/workflows", root / ".gitea/workflows"]:
        if wf_dir.is_dir():
            for wf in wf_dir.glob("*.yml"):
                if pattern in wf.read_text(errors="replace"):
                    return True
    return False


def check_actions_pinned(root: Path) -> bool:
    """Check if all 'uses:' in workflows reference SHA pins (contain @sha)."""
    for wf_dir in [root / ".github/workflows", root / ".gitea/workflows"]:
        if not wf_dir.is_dir():
            continue
        for wf in wf_dir.glob("*.yml"):
            for line in wf.read_text(errors="replace").splitlines():
                stripped = line.strip()
                if stripped.startswith("- uses:") or stripped.startswith("uses:"):
                    ref = stripped.split("@")[-1] if "@" in stripped else ""
                    # SHA pins are 40 hex chars
                    if ref and not re.match(r"[0-9a-f]{40}", ref.split()[0]):
                        return False
    return True


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
                for f in ["eslint.config.js", "eslint.config.mjs", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml"]
            ),
            "pre_commit_config": (root / ".pre-commit-config.yaml").exists(),
            "commitlint_config": any(
                (root / f).exists()
                for f in ["commitlint.config.js", "commitlint.config.mjs", ".commitlintrc.yml"]
            ),
            "gitignore": (root / ".gitignore").exists(),
            "gitignore_covers_decrypted": check_gitignore_covers(root, ".decrypted"),
            "ci_json": (root / ".ci.json").exists(),
            "renovate": (root / "renovate.json").exists() or (root / ".renovaterc.json").exists(),
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
            "compose_files": len(list(root.glob("docker-compose*.yml"))) + len(list(root.glob("compose*.yml"))),
            "dockerfile_files": sum(1 for _ in root.rglob("Dockerfile*") if not any(p in EXCLUDES for p in _.relative_to(root).parts)),
        },
        "dependencies": {
            "pytest_randomly": check_pyproject_dep(root, "pytest-randomly"),
            "test_deps_defined": check_pyproject_dep(root, "pytest") or check_pyproject_dep(root, "unittest"),
            "eslint_plugin_jest": check_package_json_dep(root, "eslint-plugin-jest"),
        },
        "ci": {
            "workflow_uses_composite_action": check_workflow_field(root, "coding-standards/docker-action"),
            "workflow_fetch_depth_zero": check_workflow_field(root, "fetch-depth: 0"),
            "workflow_persist_credentials_false": check_workflow_field(root, "persist-credentials: false"),
            "workflow_actions_sha_pinned": check_actions_pinned(root),
            "has_sha_pins": check_workflow_field(root, "@") and check_actions_pinned(root),
        },
        "acknowledged": load_acknowledged(root),
    }


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    manifest = generate(root)
    output = root / "repo-manifest.json"
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"repo-manifest.json generated ({sum(manifest['content'].values())} source files scanned)")
