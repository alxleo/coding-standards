#!/usr/bin/env python3
"""Generate docs/catalog.md — authoritative inventory of all checks.

Parses linter config, semgrep rules, conftest policies, and ruff config
to produce a single generated file. Run as drift check in CI:

    python3 scripts/generate-catalog.py --check

Sources:
  .mega-linter-default.yml  → linters + tiers
  semgrep-rules/*.yml       → semgrep rule IDs + severity + message
  policies/compose/*.rego   → compose policy rules
  policies/repo-standards/*.rego → repo-standards checks
  lint-configs-626465/ruff.toml  → ruff rule categories
"""

import re
import sys
from pathlib import Path


def extract_linters(root: Path) -> tuple[list[str], list[str]]:
    """Return (error_tier, warn_tier) linter lists."""
    ml = root / ".mega-linter-default.yml"
    text = ml.read_text()

    enable = []
    disable_errors = []
    current = None
    for line in text.splitlines():
        if "ENABLE_LINTERS:" in line:
            current = "enable"
            continue
        if "DISABLE_ERRORS_LINTERS:" in line:
            current = "disable"
            continue
        if current and line.strip().startswith("- "):
            name = line.strip().lstrip("- ").strip()
            if current == "enable":
                enable.append(name)
            else:
                disable_errors.append(name)
        elif current and not line.strip().startswith("#") and line.strip() and not line.startswith(" "):
            current = None

    error_tier = [l for l in enable if l not in disable_errors]
    warn_tier = [l for l in enable if l in disable_errors]
    return error_tier, warn_tier


def extract_semgrep_rules(root: Path) -> list[dict]:
    """Extract rule ID, severity, and first line of message from semgrep YAML."""
    import yaml

    rules = []
    for f in sorted((root / "semgrep-rules").glob("*.yml")):
        data = yaml.safe_load(f.read_text())
        for rule in data.get("rules", []):
            msg = rule.get("message", "").strip().split("\n")[0].strip()
            rules.append({
                "file": f.name,
                "id": rule["id"],
                "severity": rule.get("severity", "WARNING"),
                "message": msg,
            })
    return rules


def extract_rego_rules(policy_dir: Path, kind: str) -> list[dict]:
    """Extract warn/deny rules from Rego files."""
    rules = []
    for f in sorted(policy_dir.glob("*.rego")):
        if "_test" in f.name or f.name == "helpers.rego":
            continue
        text = f.read_text()
        # Match msg := concat(..., ["first line", ...]) or msg := sprintf("...", ...)  or msg := "..."
        for match in re.finditer(
            r'(warn|deny)\s+contains\s+msg\s+if\s*\{.*?msg\s*:=\s*'
            r'(?:concat\([^[]*\[\s*"([^"]+)"'
            r'|sprintf\(\s*"([^"]+)"'
            r'|"([^"]+)")',
            text, re.DOTALL,
        ):
            level = match.group(1)
            msg = match.group(2) or match.group(3) or match.group(4)
            rules.append({
                "file": f.name,
                "level": level,
                "message": msg.strip(),
            })
    return rules


def extract_ruff_categories(root: Path) -> list[str]:
    """Extract selected ruff rule categories from ruff.toml."""
    ruff = root / "lint-configs-626465" / "ruff.toml"
    categories = []
    in_select = False
    for line in ruff.read_text().splitlines():
        if line.strip().startswith("select"):
            in_select = True
            continue
        if in_select and line.strip() == "]":
            break
        if in_select and '"' in line:
            match = re.match(r'\s*"([^"]+)"', line)
            if match:
                cat = match.group(1)
                comment = line.split("#")[1].strip() if "#" in line else ""
                categories.append(f"{cat} — {comment}" if comment else cat)
    return categories


def generate(root: Path) -> str:
    lines = [
        "<!-- GENERATED — do not edit. Run: python3 scripts/generate-catalog.py -->",
        "# Coding Standards Catalog",
        "",
        "Complete inventory of what the coding-standards image checks.",
        "Generated from config files — this IS the source of truth.",
        "",
    ]

    # Linters
    error_tier, warn_tier = extract_linters(root)
    lines.append(f"## Linters ({len(error_tier) + len(warn_tier)} total)")
    lines.append("")
    lines.append(f"### Error tier ({len(error_tier)} — blocks build)")
    for l in error_tier:
        lines.append(f"- {l}")
    lines.append("")
    lines.append(f"### Warn tier ({len(warn_tier)} — reports only)")
    for l in warn_tier:
        lines.append(f"- {l}")
    lines.append("")

    # Ruff categories
    categories = extract_ruff_categories(root)
    lines.append(f"## Ruff rule categories ({len(categories)})")
    lines.append("")
    for c in categories:
        lines.append(f"- {c}")
    lines.append("")

    # Semgrep rules
    semgrep = extract_semgrep_rules(root)
    lines.append(f"## Semgrep rules ({len(semgrep)})")
    lines.append("")
    lines.append("| Rule | Severity | Source | Description |")
    lines.append("|------|----------|--------|-------------|")
    for r in semgrep:
        lines.append(f"| {r['id']} | {r['severity']} | {r['file']} | {r['message']} |")
    lines.append("")

    # Compose policies
    compose = extract_rego_rules(root / "policies" / "compose", "compose")
    lines.append(f"## Compose policies ({len(compose)})")
    lines.append("")
    for r in compose:
        lines.append(f"- **{r['level']}**: {r['message']} ({r['file']})")
    lines.append("")

    # Repo standards
    standards = extract_rego_rules(root / "policies" / "repo-standards", "repo-standards")
    lines.append(f"## Repo standards ({len(standards)})")
    lines.append("")
    for r in standards:
        lines.append(f"- **{r['level']}**: {r['message']} ({r['file']})")
    lines.append("")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    content = generate(root)

    if "--check" in sys.argv:
        catalog = root / "docs" / "catalog.md"
        if not catalog.exists():
            print("docs/catalog.md does not exist — run without --check to generate")
            sys.exit(1)
        existing = catalog.read_text()
        if existing != content:
            print("docs/catalog.md is out of date — regenerate with: python3 scripts/generate-catalog.py")
            sys.exit(1)
        print("docs/catalog.md is up to date")
    else:
        out = root / "docs" / "catalog.md"
        out.write_text(content)
        print(f"Generated docs/catalog.md ({len(content)} bytes)")
