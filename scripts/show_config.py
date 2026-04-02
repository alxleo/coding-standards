#!/usr/bin/env python3
"""Show which config file each linter uses and whether a workspace override shadows it.

Reads .mega-linter-default.yml for _CONFIG_FILE entries, resolves the baked-in
config path, and checks if the workspace root contains a local file that would
shadow (override) the baked config.

Usage:
    show_config.py [workspace] [--mega-linter-yml PATH]
    # default workspace: current directory
    # default yml: /opt/coding-standards/.mega-linter-default.yml
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

# Default locations inside the Docker image
_DEFAULT_YML = "/opt/coding-standards/.mega-linter-default.yml"

# Mapping from baked config basenames to common local filenames that shadow them.
# MegaLinter uses cosmiconfig or CLI flags — when a local file exists, MegaLinter
# (or the tool itself) may pick it up instead of the baked-in config.
_SHADOW_NAMES: dict[str, list[str]] = {
    "ruff.toml": ["ruff.toml", ".ruff.toml", "pyproject.toml"],
    "pyrightconfig.json": ["pyrightconfig.json"],
    ".shellcheckrc": [".shellcheckrc"],
    ".yamllint": [".yamllint", ".yamllint.yml", ".yamllint.yaml"],
    ".hadolint.yaml": [".hadolint.yaml", ".hadolint.yml"],
    ".markdownlint-cli2.yaml": [
        ".markdownlint-cli2.yaml",
        ".markdownlint-cli2.jsonc",
        ".markdownlint.json",
        ".markdownlint.yaml",
    ],
    ".prettierrc": [
        ".prettierrc",
        ".prettierrc.json",
        ".prettierrc.yml",
        "prettier.config.js",
    ],
    ".gitleaks.toml": [".gitleaks.toml"],
    ".editorconfig": [".editorconfig"],
    ".codespellrc": [".codespellrc", ".codespell", "setup.cfg"],
    ".v8rrc.yml": [".v8rrc.yml", ".v8rrc.yaml", ".v8rrc.json"],
    ".spectral.yaml": [".spectral.yaml", ".spectral.yml", ".spectral.json"],
    "eslint.config.mjs": [
        "eslint.config.mjs",
        "eslint.config.js",
        "eslint.config.cjs",
        ".eslintrc.js",
        ".eslintrc.json",
    ],
    ".tflint.hcl": [".tflint.hcl"],
    ".ls-lint.yml": [".ls-lint.yml"],
}


def _parse_yml(yml_path: Path) -> dict[str, Any]:
    """Parse MegaLinter YAML config with None guard."""
    data = yaml.safe_load(yml_path.read_text())
    if not isinstance(data, dict):
        return {}
    return data


def _extract_config_entries(data: dict[str, Any]) -> list[dict[str, str]]:
    """Extract _CONFIG_FILE entries from parsed MegaLinter config.

    Returns a list of dicts with keys: linter, config_path, config_basename.
    """
    entries = []
    for key, value in sorted(data.items()):
        if key.endswith("_CONFIG_FILE") and isinstance(value, str):
            linter = key.removesuffix("_CONFIG_FILE")
            entries.append(
                {
                    "linter": linter,
                    "config_path": value,
                    "config_basename": Path(value).name,
                }
            )
    return entries


def _find_shadows(workspace: Path, config_basename: str) -> list[str]:
    """Return list of local filenames that shadow the baked config."""
    candidates = _SHADOW_NAMES.get(config_basename, [config_basename])
    return [name for name in candidates if (workspace / name).exists()]


def show_config(workspace: Path, yml_path: Path) -> list[dict[str, str]]:
    """Build the config table rows.

    Returns list of dicts with: linter, config_file, tier, shadow.
    """
    data = _parse_yml(yml_path)
    entries = _extract_config_entries(data)
    warn_linters = set(data.get("DISABLE_ERRORS_LINTERS", []))

    rows = []
    for entry in entries:
        linter = entry["linter"]
        shadows = _find_shadows(workspace, entry["config_basename"])
        tier = "warn" if linter in warn_linters else "error"
        rows.append(
            {
                "linter": linter,
                "config_file": entry["config_basename"],
                "tier": tier,
                "shadow": ", ".join(shadows) if shadows else "",
            }
        )
    return rows


def _print_table(rows: list[dict[str, str]]) -> None:
    """Print a formatted ASCII table."""
    if not rows:
        print("No _CONFIG_FILE entries found.")
        return

    headers = {
        "linter": "Linter",
        "config_file": "Config",
        "tier": "Tier",
        "shadow": "Local Override",
    }
    cols = ["linter", "config_file", "tier", "shadow"]
    widths = {col: max(len(headers[col]), *(len(r[col]) for r in rows)) for col in cols}

    header_line = "  ".join(headers[c].ljust(widths[c]) for c in cols)
    sep_line = "  ".join("-" * widths[c] for c in cols)
    print(header_line)
    print(sep_line)
    for row in rows:
        line = "  ".join(row[c].ljust(widths[c]) for c in cols)
        print(line)

    shadow_count = sum(1 for r in rows if r["shadow"])
    print(f"\n{len(rows)} linters with baked configs. {shadow_count} overridden locally.")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    workspace = Path(".")
    yml_path = Path(_DEFAULT_YML)

    i = 0
    while i < len(args):
        if args[i] == "--mega-linter-yml" and i + 1 < len(args):
            yml_path = Path(args[i + 1])
            i += 2
        else:
            workspace = Path(args[i])
            i += 1

    if not yml_path.exists():
        print(f"Config not found: {yml_path}", file=sys.stderr)
        return 1

    rows = show_config(workspace, yml_path)
    _print_table(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
