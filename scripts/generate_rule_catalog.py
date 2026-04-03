#!/usr/bin/env python3
"""Generate rule-catalog.json — structured rule data for all configurable tools.

Extracts rule catalogs from five tools via CLI introspection, YAML parsing,
wiki scraping, or hardcoded data. Runs at build time in the Docker image
and locally for repo-committed artifact.

Usage:
    python3 scripts/generate_rule_catalog.py [--output rule-catalog.json]
"""

from __future__ import annotations

import json
import re
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

_SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _SCRIPT_DIR.parent


class Rule(TypedDict, total=False):
    id: str
    summary: str
    category: str
    severity: str
    fixable: bool


class ToolCatalog(TypedDict, total=False):
    version: str
    rule_count: int
    rules: list[Rule]
    error: str


# ── Severity normalization ──────────────────────────────────────


def _normalize_severity(severity: str, tool: str) -> str:
    """Normalize severity to: error, warning, info, ignore."""
    s = severity.lower().strip()
    mapping = {
        "error": "error",
        "err": "error",
        "deny": "error",
        "warning": "warning",
        "warn": "warning",
        "info": "info",
        "note": "info",
        "style": "info",
        "ignore": "ignore",
        "disabled": "ignore",
        "fatal": "error",
    }
    return mapping.get(s, "warning")


# ── Ruff ────────────────────────────────────────────────────────


def extract_ruff() -> ToolCatalog:
    """Extract rules via `ruff rule --all --output-format json`."""
    try:
        result = subprocess.run(
            ["ruff", "rule", "--all", "--output-format", "json"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return {
            "version": "unknown",
            "rule_count": 0,
            "rules": [],
            "error": "ruff not available",
        }

    version = "unknown"
    try:
        v = subprocess.run(
            ["ruff", "--version"], capture_output=True, text=True, timeout=10
        )
        version = v.stdout.strip().split()[-1] if v.returncode == 0 else "unknown"
    except Exception:
        pass

    raw = json.loads(result.stdout)
    rules = []
    for r in raw:
        status = r.get("status", "stable").lower()
        if status in ("removed", "deprecated"):
            continue
        rules.append(
            {
                "id": r["code"],
                "summary": r.get("summary", ""),
                "category": r.get("linter", ""),
                "severity": "warning",  # ruff doesn't have severity — all selected rules are enforced
                "fixable": r.get("fix_availability", "None") in ("Sometimes", "Always"),
            }
        )
    return {"version": version, "rule_count": len(rules), "rules": rules}


# ── Semgrep (custom rules) ─────────────────────────────────────


def extract_semgrep(root: Path) -> ToolCatalog:
    """Parse custom semgrep rules from semgrep-rules/*.yml."""
    import yaml

    rules_dir = root / "semgrep-rules"
    if not rules_dir.is_dir():
        return {"version": "custom", "rule_count": 0, "rules": []}

    rules = []
    for f in sorted(rules_dir.glob("*.yml")):
        data = yaml.safe_load(f.read_text())
        for r in data.get("rules", []):
            msg = r.get("message", "").strip().split("\n")[0].strip()
            rules.append(
                {
                    "id": r["id"],
                    "summary": msg,
                    "category": f.stem,
                    "severity": _normalize_severity(
                        r.get("severity", "WARNING"), "semgrep"
                    ),
                }
            )
    return {"version": "custom", "rule_count": len(rules), "rules": rules}


# ── Hadolint ────────────────────────────────────────────────────


def extract_hadolint() -> ToolCatalog:
    """Extract rules from hadolint wiki via shallow git clone."""
    version = "unknown"
    # Try to get version from Dockerfile
    dockerfile = REPO_ROOT / "Dockerfile"
    if dockerfile.exists():
        m = re.search(r'HADOLINT_VERSION="([^"]+)"', dockerfile.read_text())
        if m:
            version = m.group(1)

    rules = []
    wiki_dir = Path("/tmp/hadolint-wiki")

    try:
        if not wiki_dir.exists():
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "-q",
                    "https://github.com/hadolint/hadolint.wiki.git",
                    str(wiki_dir),
                ],
                check=True,
                timeout=30,
                capture_output=True,
            )
        for md in sorted(wiki_dir.glob("DL*.md")):
            rule_id = md.stem
            text = md.read_text(errors="replace")
            # First ## heading is the rule description
            m = re.search(r"^##\s*(.+)", text, re.MULTILINE)
            summary = m.group(1).strip().strip("`").strip(".") if m else ""
            # Check if rule is optional (disabled by default)
            is_optional = "optional rule which is disabled by default" in text
            severity = "ignore" if is_optional else "warning"
            rules.append(
                {
                    "id": rule_id,
                    "summary": summary,
                    "category": "dockerfile",
                    "severity": severity,
                }
            )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
        return {"version": version, "rule_count": 0, "rules": [], "error": str(e)}

    return {"version": version, "rule_count": len(rules), "rules": rules}


# ── ShellCheck ──────────────────────────────────────────────────


def extract_shellcheck() -> ToolCatalog:
    """Extract rules from shellcheck.net wiki sitemap."""
    version = "unknown"
    dockerfile = REPO_ROOT / "Dockerfile"
    if dockerfile.exists():
        m = re.search(r'SHELLCHECK_VERSION="([^"]+)"', dockerfile.read_text())
        if m:
            version = m.group(1)

    rules = []
    try:
        req = urllib.request.Request(
            "https://www.shellcheck.net/wiki/",
            headers={"User-Agent": "coding-standards-catalog/1.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        matches = re.findall(
            r"<li><a href='SC(\d+)'>SC\d+</a>\s*&ndash;\s*(.+?)</li>",
            html,
        )
        for code, desc in matches:
            # Strip HTML entities and tags
            desc = desc.replace("&ndash;", "–").replace("&amp;", "&")
            desc = re.sub(r"<[^>]+>", "", desc).replace("`", "").strip()
            rules.append(
                {
                    "id": f"SC{code}",
                    "summary": desc,
                    "category": "shell",
                    "severity": "warning",
                }
            )
    except Exception as e:
        return {"version": version, "rule_count": 0, "rules": [], "error": str(e)}

    return {"version": version, "rule_count": len(rules), "rules": rules}


# ── Dockle ──────────────────────────────────────────────────────

_DOCKLE_CHECKS = [
    ("CIS-DI-0001", "Create a user for the container", "warning"),
    ("CIS-DI-0002", "Add a HEALTHCHECK instruction to the container image", "warning"),
    ("CIS-DI-0003", "Keep Docker version up to date", "info"),
    (
        "CIS-DI-0004",
        "Do not use update instructions alone in the Dockerfile",
        "warning",
    ),
    ("CIS-DI-0005", "Enable Content trust for Docker", "info"),
    ("CIS-DI-0006", "Add HEALTHCHECK instruction to the container image", "warning"),
    (
        "CIS-DI-0007",
        "Do not use update instructions alone in the Dockerfile",
        "warning",
    ),
    ("CIS-DI-0008", "Confirm safety of setuid/setgid files", "info"),
    ("CIS-DI-0009", "Use COPY instead of ADD in Dockerfile", "warning"),
    ("CIS-DI-0010", "Do not store secrets in ENVIRONMENT variables", "warning"),
    ("CIS-DI-0011", "Install verified packages only", "info"),
    ("DKL-DI-0001", "Avoid credential configuration in Dockerfile", "warning"),
    ("DKL-DI-0002", "Avoid sudo command", "error"),
    ("DKL-DI-0003", "Avoid sensitive directory mounting", "warning"),
    ("DKL-DI-0004", "Avoid apt-get dist-upgrade", "warning"),
    ("DKL-DI-0005", "Clear apt-get caches", "warning"),
    ("DKL-DI-0006", "Avoid latest tag", "warning"),
    ("DKL-LI-0001", "Avoid empty password", "error"),
    ("DKL-LI-0002", "Avoid duplicate user/group", "error"),
    ("DKL-LI-0003", "Only necessary files in image", "info"),
]


def extract_dockle() -> ToolCatalog:
    """Return hardcoded dockle checkpoints (stable, ~20 checks)."""
    rules = [
        {
            "id": cid,
            "summary": desc,
            "category": "cis-docker" if cid.startswith("CIS") else "dockle",
            "severity": _normalize_severity(sev, "dockle"),
        }
        for cid, desc, sev in _DOCKLE_CHECKS
    ]
    return {"version": "0.4.15", "rule_count": len(rules), "rules": rules}


# ── Main ────────────────────────────────────────────────────────


def generate(root: Path) -> dict[str, object]:
    """Generate the full rule catalog."""
    catalog = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tools": {
            "ruff": extract_ruff(),
            "semgrep": extract_semgrep(root),
            "hadolint": extract_hadolint(),
            "shellcheck": extract_shellcheck(),
            "dockle": extract_dockle(),
        },
    }
    total = sum(t["rule_count"] for t in catalog["tools"].values())
    catalog["total_rules"] = total
    return catalog


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate rule-catalog.json")
    parser.add_argument(
        "--output", default="rule-catalog.json", help="Output file path"
    )
    parser.add_argument("--root", default=str(REPO_ROOT), help="Repo root path")
    args = parser.parse_args()

    root = Path(args.root)
    catalog = generate(root)

    output = Path(args.output)
    output.write_text(json.dumps(catalog, indent=2) + "\n")

    tool_summary = ", ".join(
        f"{name}: {data['rule_count']}" for name, data in catalog["tools"].items()
    )
    print(
        f"rule-catalog.json generated ({catalog['total_rules']} rules: {tool_summary})"
    )


if __name__ == "__main__":
    main()
