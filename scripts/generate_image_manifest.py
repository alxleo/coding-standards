#!/usr/bin/env python3
"""Generate image-manifest.json — cross-validation data for image integrity policies.

Parses Dockerfile, .mega-linter-default.yml, plugins/, lint-configs/, CI workflow,
and .ci.json to produce a single JSON document. Conftest policies in
policies/image-integrity/ validate invariants across these data sources.

Usage:
    python3 scripts/generate_image_manifest.py [--check]
    python3 scripts/generate_image_manifest.py > image-manifest.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml


def _find_root() -> Path:
    """Walk up from script location to find repo root (has Dockerfile)."""
    p = Path(__file__).resolve().parent.parent
    if (p / "Dockerfile").exists():
        return p
    return Path.cwd()


def _parse_megalinter_config(root: Path) -> dict[str, object]:
    """Extract linter lists and config entries from .mega-linter-default.yml."""
    config_path = root / ".mega-linter-default.yml"
    data = yaml.safe_load(config_path.read_text())

    enable = data.get("ENABLE_LINTERS", [])
    disable_errors = data.get("DISABLE_ERRORS_LINTERS", [])

    config_files = {}
    config_arguments = {}
    for key, value in data.items():
        if key.endswith("_CONFIG_FILE"):
            config_files[key] = value
        elif key.endswith("_ARGUMENTS") and isinstance(value, list):
            config_arguments[key] = value

    return {
        "enable_linters": enable,
        "disable_errors_linters": disable_errors,
        "config_files": config_files,
        "config_arguments": config_arguments,
    }


def _parse_plugins(root: Path) -> dict[str, object]:
    """Extract cli_executable from each plugin descriptor."""
    plugins = {}
    for f in sorted((root / "plugins").glob("*.megalinter-descriptor.yml")):
        data = yaml.safe_load(f.read_text())
        for linter in data.get("linters", []):
            name = linter.get("name", "")
            exe = linter.get("cli_executable", "")
            if name and exe:
                plugins[name] = {
                    "cli_executable": exe,
                    "descriptor": f.name,
                }
    return plugins


def _parse_dockerfile(root: Path) -> dict[str, object]:
    """Extract installed tools, binary checksums, and COPY sources from Dockerfile."""
    text = (root / "Dockerfile").read_text()

    # pip packages: name==version
    pip_tools = re.findall(r"(\S+)==[\d.]+", text)
    # Also catch git installs: "megalinter @ git+..."
    pip_tools.extend(re.findall(r'"(\w+)\s*@\s*git\+', text))

    # npm packages: name@version
    npm_tools = re.findall(r"(\S+)@[\d.]+", text)

    # Binary downloads: extract from Dockerfile comments (# ── toolname ──)
    # and VERSION variable assignments
    binary_tools = []
    # Map VERSION variable prefixes to actual tool names
    version_to_tool = {
        "SHELLCHECK": "shellcheck",
        "HADOLINT": "hadolint",
        "ACTIONLINT": "actionlint",
        "GITLEAKS": "gitleaks",
        "TRIVY": "trivy",
        "TFLINT": "tflint",
        "EC": "editorconfig-checker",
        "KUBECONFORM": "kubeconform",
        "LYCHEE": "lychee",
        "DOTENV": "dotenv-linter",
        "GOLANGCI": "golangci-lint",
        "SHFMT": "shfmt",
        "CHECKMAKE": "checkmake",
        "PMD": "pmd",
        "CADDY": "caddy",
        "JUST": "just",
        "CONFTEST": "conftest",
    }
    for match in re.finditer(r"(\w+)_VERSION=\"([\d.]+)\"", text):
        prefix = match.group(1)
        tool = version_to_tool.get(prefix, prefix.lower())
        binary_tools.append(tool)

    # Binary checksums: SHA256_amd64 and SHA256_arm64
    checksums: dict[str, dict[str, str]] = {}
    for match in re.finditer(r"(\w+)_SHA256_amd64=\"([a-f0-9]{64})\"", text):
        tool = version_to_tool.get(match.group(1), match.group(1).lower())
        checksums.setdefault(tool, {})["amd64"] = match.group(2)
    for match in re.finditer(r"(\w+)_SHA256_arm64=\"([a-f0-9]{64})\"", text):
        tool = version_to_tool.get(match.group(1), match.group(1).lower())
        checksums.setdefault(tool, {})["arm64"] = match.group(2)
    # Single SHA256 (no arch suffix) — arch-agnostic tools like PMD
    for match in re.finditer(r"(\w+)_SHA256=\"([a-f0-9]{64})\"", text):
        tool = version_to_tool.get(match.group(1), match.group(1).lower())
        if tool not in checksums:
            checksums[tool] = {"arch_agnostic": match.group(2)}

    # COPY sources
    copy_sources = []
    for match in re.finditer(r"COPY\s+(?:--chmod=\S+\s+)?(\S+)", text):
        src = match.group(1)
        if not src.startswith("--"):
            copy_sources.append(src)

    return {
        "pip": sorted(set(pip_tools)),
        "npm": sorted(set(npm_tools)),
        "binary": sorted(set(binary_tools)),
        "binary_checksums": checksums,
        "copy_sources": sorted(set(copy_sources)),
    }


def _parse_ci_hash(root: Path) -> list[str]:
    """Extract hashFiles() patterns from CI workflow's Docker context hash."""
    ci_path = root / ".github" / "workflows" / "ci.yml"
    if not ci_path.exists():
        return []
    text = ci_path.read_text()
    # Target the CTX_HASH line specifically (Docker build context), not other hashFiles
    match = re.search(r"CTX_HASH:.*hashFiles\(([^)]+)\)", text)
    if not match:
        return []
    return re.findall(r"'([^']+)'", match.group(1))


def _list_lint_configs(root: Path) -> list[str]:
    """List config files in lint-configs/ (excluding caches and dirs)."""
    configs_dir = root / "lint-configs"
    skip_suffixes = ("_cache",)
    return sorted(
        f.name for f in configs_dir.iterdir() if f.is_file() and not any(f.name.endswith(s) for s in skip_suffixes)
    )


def _parse_ci_json(root: Path) -> list[str]:
    """Extract smoke test commands from .ci.json."""
    ci_json = root / ".ci.json"
    data = json.loads(ci_json.read_text())
    return data.get("test_commands", [])


def generate_manifest(root: Path) -> dict[str, object]:
    """Generate the complete image manifest."""
    ml_config = _parse_megalinter_config(root)
    plugins = _parse_plugins(root)
    dockerfile = _parse_dockerfile(root)
    ci_hash = _parse_ci_hash(root)
    lint_configs = _list_lint_configs(root)
    smoke_tests = _parse_ci_json(root)

    return {
        **ml_config,
        "plugins": plugins,
        "dockerfile_tools": {
            "pip": dockerfile["pip"],
            "npm": dockerfile["npm"],
            "binary": dockerfile["binary"],
        },
        "dockerfile_binary_checksums": dockerfile["binary_checksums"],
        "dockerfile_copy_sources": dockerfile["copy_sources"],
        "ci_hash_patterns": ci_hash,
        "lint_config_files": lint_configs,
        "smoke_test_commands": smoke_tests,
    }


def main() -> None:
    root = _find_root()
    manifest = generate_manifest(root)

    if "--check" in sys.argv:
        # Verify manifest can be generated without errors
        print(
            f"Image manifest: {len(manifest['enable_linters'])} linters, "
            f"{len(manifest['plugins'])} plugins, "
            f"{len(manifest['dockerfile_tools']['binary'])} binaries"
        )
        return

    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
