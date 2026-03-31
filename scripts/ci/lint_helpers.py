"""Shared helpers for CI scripts — replaces lib/common.sh."""

from __future__ import annotations

import re
from pathlib import Path

# Noise patterns to filter from lint logs
NOISE_RE = re.compile(
    r"^\[INFO\]|^- Installing|^- Using|^Initializing"
    r"|^- repo:|^\s*$|^::group|^::endgroup|^::"
)

# Pre-commit banner lines (e.g. "Check YAML...Passed", "Shell hygiene...Failed")
BANNER_RE = re.compile(r"\.{3,}(Passed|Failed|Skipped)")


def parse_groups(
    conf_path: str | Path,
) -> list[tuple[str, str, str, str]]:
    """Parse groups.conf into (logkey, display, context, step) tuples."""
    expected_fields = 4  # logkey|display|context|step
    groups = []
    with open(conf_path) as f:
        for raw_line in f:
            stripped = raw_line.strip()
            # Skip blank lines and comments in groups.conf
            if not stripped or stripped.startswith("#"):  # nosemgrep: python-silent-fallback-or
                continue
            parts = stripped.split("|")
            if len(parts) == expected_fields:
                groups.append((parts[0], parts[1], parts[2], parts[3]))
    return groups


def extract_errors(logfile: str | Path, limit: int = 5) -> list[str]:
    """Extract up to N meaningful error lines from a lint log file."""
    path = Path(logfile)
    if not path.exists():
        return []

    lines = path.read_text().splitlines()
    errors = []
    error_re = re.compile(
        r"(ERROR|Error:|error:|CRITICAL|warning:|^\S+:[0-9]+:|reported issue)"
    )

    for line in lines:
        if NOISE_RE.search(line):
            continue
        if BANNER_RE.search(line):
            continue
        if error_re.search(line):
            errors.append(line)
            if len(errors) >= limit:
                break

    return errors


def extract_hint(logfile: str | Path, max_len: int = 140) -> str:
    """Extract a single short hint line for commit status descriptions.

    Priority: file:line errors > keyword errors > last meaningful line > banner.
    """
    path = Path(logfile)
    if not path.exists():
        return ""

    lines = path.read_text().splitlines()

    # 1. Specific file:line references (most actionable)
    for line in lines:
        if re.match(r"^\S+:[0-9]+:", line) and not BANNER_RE.search(line):
            return line.strip()[:max_len]

    # 2. Keyword errors (excluding banners)
    keyword_re = re.compile(r"(ERROR|Error:|error:|CRITICAL|FATAL|reported issue)")
    for line in lines:
        if keyword_re.search(line) and not BANNER_RE.search(line):
            return line.strip()[:max_len]

    # 3. Last meaningful line as fallback
    meaningful = [
        line
        for line in lines
        if not NOISE_RE.search(line)
        and not BANNER_RE.search(line)
        and not re.match(r"^- hook id:|^- exit code:", line)
    ]
    if meaningful:
        return meaningful[-1].strip()[:max_len]

    # 4. Banner line (better than nothing)
    for line in lines:
        if BANNER_RE.search(line):
            return line.strip()[:max_len]

    return ""
