#!/usr/bin/env python3
"""Scan files for expired date markers and fail if any are past due.

Supports markers: REMOVE_AFTER, DEPRECATE_BY, TODO(YYYY-MM-DD)

Usage:
  check-expiry.py [directories...]     # default: current directory
  check-expiry.py --pattern "SUNSET:"  # custom marker pattern

Output: file:line: marker expired (was YYYY-MM-DD, today is YYYY-MM-DD)
"""

import argparse
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

DEFAULT_PATTERNS = [
    r"REMOVE_AFTER:\s*(\d{4}-\d{2}-\d{2})",
    r"DEPRECATE_BY:\s*(\d{4}-\d{2}-\d{2})",
    r"TODO\((\d{4}-\d{2}-\d{2})\)",
]


def scan_file(path: Path, patterns: list[re.Pattern], today: date) -> list[str]:
    findings = []
    try:
        text = path.read_text(errors="replace")
    except (OSError, UnicodeDecodeError):
        return findings
    for i, line in enumerate(text.splitlines(), 1):
        for pattern in patterns:
            for match in pattern.finditer(line):
                try:
                    expiry = date.fromisoformat(match.group(1))
                except ValueError:
                    findings.append(f"{path}:{i}: invalid date in marker: {match.group(1)}")
                    continue
                if expiry < today:
                    findings.append(f"{path}:{i}: expired marker (was {expiry}, today is {today})")
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dirs", nargs="*", default=["."])
    parser.add_argument("--pattern", action="append", default=[])
    parser.add_argument("--ext", default=".yml,.yaml,.sh,.py,.tf,.md,.toml,.cfg")
    args = parser.parse_args()

    raw_patterns = args.pattern or DEFAULT_PATTERNS  # nosemgrep: coding-standards.python-silent-fallback-or
    patterns = [re.compile(p) for p in raw_patterns]
    extensions = set(args.ext.split(","))
    today = datetime.now(tz=UTC).date()
    findings = []

    for d in args.dirs:
        for path in Path(d).rglob("*"):
            if path.suffix in extensions and path.is_file():
                findings.extend(scan_file(path, patterns, today))

    for f in findings:
        print(f)

    if findings:
        print(f"\n{len(findings)} expired marker(s) found.")
        sys.exit(1)
    print("No expired markers found.")


if __name__ == "__main__":
    main()
