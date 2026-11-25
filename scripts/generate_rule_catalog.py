#!/usr/bin/env python3
"""Generate rule-catalog.json — structured rule data for supported tools.

Extracts rule catalogs via CLI introspection, YAML parsing, and wiki scraping.
Generated at build time into the Docker image. Local generation is optional
for inspection or debugging.

Usage:
    python3 scripts/generate_rule_catalog.py [--output rule-catalog.json]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError, field_validator
from show_catalog import extract_semgrep_rules

_SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _SCRIPT_DIR.parent


# ── Severity normalization ──────────────────────────────────────


def _normalize_severity(severity: str) -> str:
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


_RUFF_STATUS_FIELDS = TypeAdapter(dict[str, object])


class _RuffRuleSpec(BaseModel):
    code: str | None
    summary: str = ""
    linter: str | None = ""
    fix_availability: str = "None"
    status: str = "stable"

    @field_validator("status", mode="before")
    @classmethod
    def _parse_status(cls, value: object) -> object:
        # Ruff versions emit a status string or a one-key status object.
        try:
            fields = _RUFF_STATUS_FIELDS.validate_python(value, strict=True)
        except ValidationError:
            return value
        return next(iter(fields), "stable")


_RUFF_RULES = TypeAdapter(list[_RuffRuleSpec])


def extract_ruff() -> dict[str, Any]:
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
            ["ruff", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        version = v.stdout.strip().split()[-1] if v.returncode == 0 else "unknown"
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        OSError,
    ):
        pass

    rules = []
    for rule in _RUFF_RULES.validate_json(result.stdout, strict=True):
        if rule.status.lower() in ("removed", "deprecated"):
            continue
        rules.append(
            {
                "id": rule.code,
                "summary": rule.summary,
                "category": rule.linter,
                "severity": "warning",  # ruff doesn't have severity — all selected rules are enforced
                "fixable": rule.fix_availability in ("Sometimes", "Always"),
            }
        )
    return {"version": version, "rule_count": len(rules), "rules": rules}


# ── Semgrep (custom rules) ─────────────────────────────────────


def extract_semgrep(root: Path) -> dict[str, Any]:
    """Map custom Semgrep rules to the generated catalog fields."""
    rules = [
        {
            "id": rule["id"],
            "summary": rule["message"],
            "category": Path(rule["file"]).stem,
            "severity": _normalize_severity(rule["severity"]),
        }
        for rule in extract_semgrep_rules(root)
    ]
    return {"version": "custom", "rule_count": len(rules), "rules": rules}


# ── Hadolint ────────────────────────────────────────────────────


def extract_hadolint(root: Path | None = None) -> dict[str, Any]:
    """Extract rules from hadolint wiki via shallow git clone."""
    version = "unknown"
    for candidate in [root, REPO_ROOT]:
        if candidate is None:
            continue
        dockerfile = candidate / "Dockerfile"
        if dockerfile.exists():
            m = re.search(r'HADOLINT_VERSION="([^"]+)"', dockerfile.read_text())
            if m:
                version = m.group(1)
                break

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


def extract_shellcheck(root: Path | None = None) -> dict[str, Any]:
    """Extract rules from shellcheck.net wiki sitemap."""
    version = "unknown"
    for candidate in [root, REPO_ROOT]:
        if candidate is None:
            continue
        dockerfile = candidate / "Dockerfile"
        if dockerfile.exists():
            m = re.search(r'SHELLCHECK_VERSION="([^"]+)"', dockerfile.read_text())
            if m:
                version = m.group(1)
                break

    rules = []
    try:
        req = urllib.request.Request(
            "https://www.shellcheck.net/wiki/",
            headers={"User-Agent": "coding-standards-catalog/1.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosemgrep: dynamic-urllib-use-detected
            html = resp.read().decode("utf-8", errors="replace")

        matches = re.findall(
            r"<li><a href='SC(\d+)'>SC\d+</a>\s*&ndash;\s*(.+?)</li>",
            html,
        )
        for code, raw_desc in matches:
            # Strip HTML entities and tags
            clean = raw_desc.replace("&ndash;", "-").replace("&amp;", "&")
            clean = re.sub(r"<[^>]+>", "", clean).replace("`", "").strip()
            rules.append(
                {
                    "id": f"SC{code}",
                    "summary": clean,
                    "category": "shell",
                    "severity": "warning",
                }
            )
    except (OSError, urllib.error.URLError) as e:
        return {"version": version, "rule_count": 0, "rules": [], "error": str(e)}

    if not rules:
        return {
            "version": version,
            "rule_count": 0,
            "rules": [],
            "error": "wiki parse returned 0 rules — format may have changed",
        }

    return {"version": version, "rule_count": len(rules), "rules": rules}


# ── Main ────────────────────────────────────────────────────────


def generate(root: Path) -> dict[str, Any]:
    """Generate the full rule catalog."""
    catalog = {
        "generated_at": datetime.now(UTC).isoformat(),
        "tools": {
            "ruff": extract_ruff(),
            "semgrep": extract_semgrep(root),
            "hadolint": extract_hadolint(root),
            "shellcheck": extract_shellcheck(root),
        },
    }
    total = sum(t["rule_count"] for t in catalog["tools"].values())
    catalog["total_rules"] = total
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate rule-catalog.json")
    parser.add_argument("--output", default="rule-catalog.json", help="Output file path")
    parser.add_argument("--root", default=str(REPO_ROOT), help="Repo root path")
    args = parser.parse_args()

    root = Path(args.root)
    catalog = generate(root)

    output = Path(args.output)
    output.write_text(json.dumps(catalog, indent=2) + "\n")

    tool_summary = ", ".join(f"{name}: {data['rule_count']}" for name, data in catalog["tools"].items())
    print(f"rule-catalog.json generated ({catalog['total_rules']} rules: {tool_summary})")


if __name__ == "__main__":
    main()
