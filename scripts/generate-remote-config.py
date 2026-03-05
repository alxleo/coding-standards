#!/usr/bin/env python3
"""Generate .pre-commit-config.remote.yaml from .pre-commit-config.yaml.

Copies the baseline config and injects --config args for tools that need
explicit config paths when run from consumer repos.

Usage:
    uv run scripts/generate-remote-config.py
    uv run scripts/generate-remote-config.py --check  # drift detection
"""

import argparse
import re
import sys
from pathlib import Path

BASELINE = Path("configs/.pre-commit-config.yaml")
REMOTE = Path("configs/.pre-commit-config.remote.yaml")

# Map hook IDs to the --config arg they need in consumer repos.
# Only hooks that auto-discover config from repo root need this.
CONFIG_OVERRIDES = {
    "gitleaks": ["--config", ".coding-standards/configs/.gitleaks.toml"],
    "markdownlint-cli2": [
        "--config",
        ".coding-standards/configs/.markdownlint-cli2.yaml",
    ],
    "commitlint": ["--config", ".coding-standards/configs/commitlint.config.mjs"],
}

HEADER = """\
# AUTO-GENERATED from .pre-commit-config.yaml — do not edit manually.
# Regenerate: uv run scripts/generate-remote-config.py
#
# For consumer repos that fetch coding-standards at runtime.
# Identical to .pre-commit-config.yaml except tools that need config files
# get explicit --config args pointing to .coding-standards/configs/.
"""


def generate(baseline_text: str) -> str:
    lines = baseline_text.splitlines()
    out = HEADER.rstrip().splitlines()

    # Drop original comment header (lines starting with # before first non-comment)
    i = 0
    while i < len(lines) and (lines[i].startswith("#") or lines[i].strip() == ""):
        i += 1

    # Remove the exclude: ^tests/fixtures/ line (not relevant for consumer repos)
    remaining = lines[i:]
    remaining = [line for line in remaining if not re.match(r"^exclude:\s", line)]

    # Process line by line, injecting args where needed
    result = out + [""] + remaining
    output = "\n".join(result) + "\n"

    # Inject --config args for each hook that needs it
    for hook_id, args in CONFIG_OVERRIDES.items():
        args_yaml = "[" + ", ".join(args) + "]"

        # Pattern: "      - id: <hook_id>\n" possibly followed by existing args
        # We need to add args line after the id line
        pattern = rf"(      - id: {re.escape(hook_id)}\n)"
        replacement = rf"\1        args: {args_yaml}\n"

        # Check if hook already has args — if so, prepend our config args
        args_pattern = rf"(      - id: {re.escape(hook_id)}\n        args: \[)"
        if re.search(args_pattern, output):
            # Hook has existing args — prepend our config args
            output = re.sub(
                args_pattern,
                r"\g<1>" + ", ".join(args) + ", ",
                output,
            )
        else:
            # Hook has no args — add args line
            output = re.sub(pattern, replacement, output)

    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="Check if remote config is up to date"
    )
    args = parser.parse_args()

    if not BASELINE.exists():
        print(f"ERROR: {BASELINE} not found", file=sys.stderr)
        return 1

    baseline_text = BASELINE.read_text()
    generated = generate(baseline_text)

    if args.check:
        if not REMOTE.exists():
            print(f"ERROR: {REMOTE} not found", file=sys.stderr)
            return 1
        current = REMOTE.read_text()
        if current == generated:
            print("remote config is up to date.")
            return 0
        else:
            print("remote config is STALE — regenerate with:")
            print("  uv run scripts/generate-remote-config.py")
            return 1

    REMOTE.write_text(generated)
    print(f"Generated {REMOTE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
