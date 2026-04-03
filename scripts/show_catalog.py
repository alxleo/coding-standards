#!/usr/bin/env python3
"""Authoritative inventory of all checks.

Parses linter config, semgrep rules, conftest policies, and ruff config.
Use --rules for per-tool rule details from rule-catalog.json.

Sources:
  .mega-linter-default.yml  → linters + tiers
  semgrep-rules/*.yml       → semgrep rule IDs + severity + message
  policies/compose/*.rego   → compose policy rules
  policies/repo-standards/*.rego → repo-standards checks
  lint-configs/ruff.toml  → ruff rule categories
"""

import re
from pathlib import Path
from typing import Any


def extract_linters(root: Path) -> tuple[list[str], list[str]]:
    """Return (error_tier, warn_tier) linter lists."""
    import yaml

    ml = root / ".mega-linter-default.yml"
    data = yaml.safe_load(ml.read_text())
    enable = data.get("ENABLE_LINTERS", [])
    disable_errors = set(data.get("DISABLE_ERRORS_LINTERS", []))
    error_tier = [n for n in enable if n not in disable_errors]
    warn_tier = [n for n in enable if n in disable_errors]
    if len(error_tier) + len(warn_tier) != len(enable):
        msg = f"Tier count mismatch: {len(error_tier)} error + {len(warn_tier)} warn != {len(enable)} enabled"
        raise ValueError(msg)
    return error_tier, warn_tier


def extract_semgrep_rules(root: Path) -> list[dict]:
    """Extract rule ID, severity, and first line of message from semgrep YAML."""
    import yaml

    rules = []
    for f in sorted((root / "semgrep-rules").glob("*.yml")):
        data = yaml.safe_load(f.read_text())
        for rule in data.get("rules", []):
            msg = rule.get("message", "").strip().split("\n")[0].strip()
            rules.append(
                {
                    "file": f.name,
                    "id": rule["id"],
                    "severity": rule.get("severity", "WARNING"),
                    "message": msg,
                }
            )
    return rules


def extract_rego_rules(policy_dir: Path, _kind: str) -> list[dict]:
    """Extract warn/deny rules from Rego files."""
    rules = []
    for f in sorted(policy_dir.glob("*.rego")):
        # Skip test files and shared helper module
        if "_test" in f.name or f.name == "helpers.rego":  # nosemgrep: coding-standards.python-silent-fallback-or
            continue
        text = f.read_text()
        # Match msg := concat/sprintf/string patterns, extract first quoted string
        for match in re.finditer(
            r"(warn|deny)\s+contains\s+msg\s+if\s*\{.*?msg\s*:=\s*"
            r'(?:sprintf\(concat\([^[]*\[\s*"([^"]+)"'
            r'|concat\([^[]*\[\s*"([^"]+)"'
            r'|sprintf\(\s*"([^"]+)"'
            r'|"([^"]+)")',
            text,
            re.DOTALL,
        ):
            level = match.group(1)
            # First non-None capture group is the message text
            msg = next((g for i in (2, 3, 4, 5) if (g := match.group(i))), "")
            rules.append(
                {
                    "file": f.name,
                    "level": level,
                    "message": msg.strip(),
                }
            )
    return rules


def _find_lint_configs(root: Path) -> Path:
    """Find lint-configs directory (different name locally vs in container)."""
    tried: list[Path] = []
    for name in ("lint-configs", "configs"):
        p = root / name
        if p.is_dir():
            return p
        tried.append(p)
    tried_str = ", ".join(str(p) for p in tried)
    msg = f"Cannot find lint configs directory under {root}; tried: {tried_str}"
    raise FileNotFoundError(msg)


def extract_ruff_categories(root: Path) -> list[str]:
    """Extract selected ruff rule categories from ruff.toml."""
    ruff = _find_lint_configs(root) / "ruff.toml"
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
    lines.append("")
    lines.extend(f"- {name}" for name in error_tier)
    lines.append("")
    lines.append(f"### Warn tier ({len(warn_tier)} — reports only)")
    lines.append("")
    lines.extend(f"- {name}" for name in warn_tier)
    lines.append("")

    # Ruff categories
    categories = extract_ruff_categories(root)
    lines.append(f"## Ruff rule categories ({len(categories)})")
    lines.append("")
    lines.extend(f"- {c}" for c in categories)
    lines.append("")

    # Semgrep rules
    semgrep = extract_semgrep_rules(root)
    lines.append(f"## Semgrep rules ({len(semgrep)})")
    lines.append("")
    lines.append("| Rule | Severity | Source | Description |")
    lines.append("|------|----------|--------|-------------|")
    lines.extend(f"| {r['id']} | {r['severity']} | {r['file']} | {r['message']} |" for r in semgrep)
    lines.append("")

    # Compose policies
    compose = extract_rego_rules(root / "policies" / "compose", "compose")
    lines.append(f"## Compose policies ({len(compose)})")
    lines.append("")
    lines.extend(f"- **{r['level']}**: {r['message']} ({r['file']})" for r in compose)
    lines.append("")

    # Repo standards
    standards = extract_rego_rules(root / "policies" / "repo-standards", "repo-standards")
    lines.append(f"## Repo standards ({len(standards)})")
    lines.append("")
    lines.extend(f"- **{r['level']}**: {r['message']} ({r['file']})" for r in standards)

    return "\n".join(lines) + "\n"


def _load_rule_catalog(root: Path) -> dict[str, Any] | None:
    """Load rule-catalog.json if it exists."""
    for candidate in [
        root / "rule-catalog.json",
        Path("/opt/coding-standards/rule-catalog.json"),
    ]:
        if candidate.exists():
            import json

            try:
                return json.loads(candidate.read_text())
            except (json.JSONDecodeError, OSError) as e:
                import sys

                print(f"Error reading {candidate}: {e}", file=sys.stderr)
                return None
    import sys

    print("rule-catalog.json not found. Run generate_rule_catalog.py first.", file=sys.stderr)
    return None


def render_rules(catalog: dict[str, Any], tool_filter: str | None = None, fmt: str = "md") -> str:
    """Render per-tool rule data from rule-catalog.json."""
    import json

    tools = catalog.get("tools", {})
    if tool_filter:
        tools = {k: v for k, v in tools.items() if k == tool_filter}
        if not tools:
            return f"Unknown tool: {tool_filter}\n"

    if fmt == "json":
        return json.dumps(tools, indent=2) + "\n"

    lines = [
        f"# Rule Catalog ({catalog.get('total_rules', '?')} rules)",
        "",
    ]
    for name, data in tools.items():
        err = data.get("error")
        lines.append(f"## {name} — {data.get('rule_count', '?')} rules (v{data.get('version', '?')})")
        if err:
            lines.append(f"  *Error: {err}*")
        lines.append("")
        lines.append("| ID | Severity | Category | Description |")
        lines.append("|----|----------|----------|-------------|")
        lines.extend(
            f"| {r.get('id', '?')} | {r.get('severity', '?')} | {r.get('category', '')} | {r.get('summary', '')[:80]} |"
            for r in data.get("rules", [])
        )
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Show coding-standards catalog")
    parser.add_argument(
        "--rules",
        action="store_true",
        help="Show per-tool rule details from rule-catalog.json",
    )
    parser.add_argument("--tool", help="Filter rules to a specific tool (e.g. hadolint, ruff)")
    parser.add_argument("--format", choices=["md", "json"], default="md", help="Output format")
    args = parser.parse_args()

    # Inside Docker: configs at /opt/coding-standards/
    # Local: repo root
    root = Path("/opt/coding-standards")
    if not (root / "configs").exists():
        root = Path(__file__).resolve().parent.parent

    if args.rules:
        catalog = _load_rule_catalog(root)
        if not catalog:
            # _load_rule_catalog prints specific error for corrupt files
            raise SystemExit(1)
        print(render_rules(catalog, tool_filter=args.tool, fmt=args.format))
    else:
        print(generate(root))


if __name__ == "__main__":
    main()
