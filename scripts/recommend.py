#!/usr/bin/env python3
"""Recommend checks for a consumer repo based on detected stack.

Scans the workspace, identifies what's running vs what COULD run,
and outputs actionable setup instructions. Designed for LLM consumers.

Usage:
    python3 /opt/coding-standards/scripts/recommend.py [workspace]
    docker run ... coding-standards:latest recommend
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

WORKSPACE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/lint")

# Resolve the coding-standards repo root for reading baked source files.
# In Docker: /opt/coding-standards. In dev: the repo root (parent of scripts/).
_SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _SCRIPT_DIR.parent


def _discover_semgrep_rules() -> list[dict[str, str]]:
    """Extract rule IDs and messages from semgrep-rules/*.yml."""
    rules_dir = REPO_ROOT / "semgrep-rules"
    if not rules_dir.is_dir():
        return []

    results: list[dict[str, str]] = []
    for yml_path in sorted(rules_dir.glob("*.yml")):
        try:
            data = yaml.safe_load(yml_path.read_text())
        except (yaml.YAMLError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        for rule in data.get("rules", []):
            rule_id = rule.get("id", "")
            message = rule.get("message", "").strip()
            # Collapse multiline YAML messages into a single line
            message = re.sub(r"\s+", " ", message)
            if rule_id:
                results.append({"id": rule_id, "message": message, "file": yml_path.name})
    return results


def _discover_conftest_policies() -> list[dict[str, str | list[str]]]:
    """Extract package names and rule types from policies/{compose,repo-standards}/*.rego."""
    results: list[dict[str, str | list[str]]] = []
    for policy_subdir in ("compose", "repo-standards"):
        policy_dir = REPO_ROOT / "policies" / policy_subdir
        if not policy_dir.is_dir():
            continue
        for rego_path in sorted(policy_dir.glob("*.rego")):
            # Skip test files and helper-only files
            if rego_path.name.endswith("_test.rego"):
                continue

            try:
                content = rego_path.read_text()
            except OSError:
                continue

            # Extract package name
            pkg_match = re.search(r"^package\s+(\S+)", content, re.MULTILINE)
            if not pkg_match:
                continue
            package = pkg_match.group(1)

            # Detect rule types present in the file
            rule_types = [t for t in ("deny", "warn") if re.search(rf"^{t}\s+contains", content, re.MULTILINE)]

            if rule_types:
                results.append(
                    {
                        "package": package,
                        "types": rule_types,
                        "file": rego_path.name,
                    }
                )
    return results


def has_files(patterns: list[str]) -> list[str]:
    """Check which glob patterns match files in the workspace."""
    return [p for p in patterns if list(WORKSPACE.rglob(p))]


def file_exists(name: str) -> bool:
    return (WORKSPACE / name).exists()


# ── Detection rules ──────────────────────────────────────────
# Each recommendation: what we detect, what's missing, what to do.

recommendations: list[dict[str, object]] = []

# Conftest compose policies
if has_files(["docker-compose*.yml", "compose*.yml"]) and not file_exists("conftest.toml"):
    recommendations.append(
        {
            "tool": "conftest",
            "reason": "Docker Compose files detected but no conftest.toml",
            "value": "Structural validation: healthchecks, resource limits, image pinning, security",
            "setup": [
                "echo 'parser = \"yaml\"' > conftest.toml",
                "mkdir -p policy/compose",
                "# Add .rego policies — see: just cs-help conftest",
            ],
            "baked_policies": "Image validates compose files against baked policies."
            " conftest.toml activates consumer-side policies too.",
        }
    )

# Custom semgrep rules
if has_files(["*.py", "*.js", "*.ts"]) and not (WORKSPACE / ".semgrep").exists():
    recommendations.append(
        {
            "tool": "semgrep (custom rules)",
            "reason": "Code files detected but no .semgrep/ directory",
            "value": "Catch project-specific anti-patterns alongside baked security rules",
            "setup": [
                "mkdir -p .semgrep",
                "# Add YAML rules — see: just cs-help semgrep",
            ],
        }
    )

# Pyright config for Python repos
if has_files(["*.py"]) and not file_exists("pyrightconfig.json"):
    recommendations.append(
        {
            "tool": "pyright",
            "reason": "Python files detected but no pyrightconfig.json",
            "value": "Type checking catches hallucinated APIs, wrong argument types, missing imports",
            "setup": [
                'echo \'{"typeCheckingMode": "standard", "pythonVersion": "3.11"}\' > pyrightconfig.json',
            ],
        }
    )

# Gitleaks config
if not file_exists(".gitleaks.toml") and not file_exists(".gitleaksignore"):
    recommendations.append(
        {
            "tool": "gitleaks",
            "reason": "No .gitleaks.toml or .gitleaksignore — using defaults",
            "value": "Custom allowlists prevent false positives on test fixtures and known-safe patterns",
            "setup": [
                "# Create .gitleaks.toml to allowlist known-safe patterns:",
                "# [allowlist]",
                '#   paths = ["test/fixtures/**"]',
            ],
        }
    )

# Trivy ignore for known CVEs
if has_files(["Dockerfile", "docker-compose*.yml"]) and not file_exists(".trivyignore"):
    recommendations.append(
        {
            "tool": "trivy",
            "reason": "Docker files detected but no .trivyignore",
            "value": "Silence accepted CVEs so trivy only reports new vulnerabilities",
            "setup": [
                "# Create .trivyignore with accepted CVE IDs:",
                "# CVE-2024-XXXXX  # accepted: no exposure in our usage",
            ],
        }
    )

# Dependency cruiser for JS/TS
if has_files(["package.json"]) and not has_files([".dependency-cruiser.*"]):
    recommendations.append(
        {
            "tool": "dependency-cruiser",
            "reason": "package.json detected but no dependency-cruiser config",
            "value": "Enforce module boundaries and catch circular dependencies",
            "setup": [
                "npx depcruise --init",
                "# Generates .dependency-cruiser.cjs with sensible defaults",
            ],
        }
    )

# Ansible lint config
if has_files(["*/tasks/*.yml", "*/playbooks/*.yml", "ansible.cfg"]) and not file_exists(".ansible-lint"):
    recommendations.append(
        {
            "tool": "ansible-lint",
            "reason": "Ansible files detected but no .ansible-lint config",
            "value": "Custom skip rules and exclude paths for your playbook structure",
            "setup": [
                "# Create .ansible-lint:",
                "# skip_list:",
                "#   - yaml[truthy]  # if you use 'yes' in YAML",
                "# exclude_paths:",
                "#   - .cache/",
            ],
        }
    )

# Ruff config for Python repos
if has_files(["*.py"]) and not file_exists("ruff.toml"):
    recommendations.append(
        {
            "tool": "ruff",
            "reason": "Python files detected but no ruff.toml — using baked defaults",
            "value": "Custom rule selection, per-file ignores, line length. Extend the baseline or replace it.",
            "setup": [
                "# Extend baked config:",
                "# echo 'extend = \".mega-linter-config/ruff.toml\"' > ruff.toml",
                "# Or see: just cs-help ruff",
            ],
        }
    )

# ESLint config for JS/TS repos
if has_files(["*.js", "*.ts", "*.tsx"]) and not has_files(["eslint.config.*"]):
    recommendations.append(
        {
            "tool": "eslint",
            "reason": "JS/TS files detected but no eslint.config.mjs — using baked defaults",
            "value": "Custom rules, plugin selection, framework-specific config",
            "setup": [
                "# Create eslint.config.mjs with your rules",
                "# Set in .mega-linter.yml: JAVASCRIPT_ES_CONFIG_FILE: eslint.config.mjs",
                "# See: just cs-help eslint",
            ],
        }
    )

# Shellcheck config
if has_files(["*.sh"]) and not file_exists(".shellcheckrc"):
    recommendations.append(
        {
            "tool": "shellcheck",
            "reason": "Shell scripts detected but no .shellcheckrc — using baked defaults",
            "value": "Custom severity levels, disabled checks, source paths for sourced files",
            "setup": [
                "# Create .shellcheckrc:",
                "# source-path=scripts",
                "# disable=SC2086",
            ],
        }
    )

# Yamllint config
if has_files(["*.yml", "*.yaml"]) and not file_exists(".yamllint"):
    recommendations.append(
        {
            "tool": "yamllint",
            "reason": "YAML files detected but no .yamllint — using baked defaults",
            "value": "Custom line length, truthy values, comment indentation rules",
            "setup": [
                "# Create .yamllint to override specific rules",
                "# See baked config: .mega-linter-config/.yamllint",
            ],
        }
    )

# Commitlint
if not has_files(["commitlint.config.*"]):
    recommendations.append(
        {
            "tool": "commitlint",
            "reason": "No commitlint config — conventional commits not enforced",
            "value": "Enforces consistent commit message format (feat:, fix:, etc.)",
            "setup": [
                "# Baked config enforces conventional commits.",
                "# To use: just add commitlint.config.mjs to your repo",
                "# (or accept the baked default which activates automatically)",
            ],
        }
    )

# Repo standards acknowledgments
if file_exists("repo-manifest.json") and not file_exists(".repo-standards.yml"):
    recommendations.append(
        {
            "tool": "repo-standards",
            "reason": "Repo-standards checks run but no acknowledgment file",
            "value": "Acknowledge warnings that don't apply with documented reasons",
            "setup": [
                "# Create .repo-standards.yml:",
                "# acknowledged:",
                '#   pydantic: "scripts only, no boundary-crossing data"',
            ],
        }
    )


# ── Baked checks discovery ───────────────────────────────────

baked_checks = {
    "semgrep_rules": _discover_semgrep_rules(),
    "conftest_policies": _discover_conftest_policies(),
}

# ── Output ────────────────────────────────────────────────────

output = {
    "status": "recommendations_available" if recommendations else "fully_configured",
    "count": len(recommendations),
    "recommendations": recommendations,
    "baked_checks": baked_checks,
}
print(json.dumps(output, indent=2))
