#!/usr/bin/env python3
"""Extract per-linter timing data from MegaLinter reports.

Parses the markdown report table (mega-linter-report.json elapsed_time_s
is not populated by MegaLinter — known gap). Outputs structured JSON
for baseline comparison and trend tracking.

Usage:
    python3 scripts/extract_linter_timings.py [--report-dir DIR] [--format json|table]
"""

import json
import re
import sys
from pathlib import Path


def parse_report_markdown(report_path: Path) -> list[dict]:
    """Parse the MegaLinter markdown report table for timing data.

    The table format is:
    | Descriptor | Linter | Files | Fixed | Errors | Warnings | Elapsed time |
    """
    text = report_path.read_text()
    timings = []

    # Match table rows: |status DESCRIPTOR|[linter](url)|files|fixed|errors|warnings|time|
    row_pattern = re.compile(
        r"\|[^\|]*?"  # status + descriptor
        r"(\w[\w_-]*)"  # capture descriptor name
        r"\s*\|"
        r"\[([^\]]+)\]"  # capture linter name
        r"[^\|]*\|"  # rest of linter cell
        r"\s*(\S+)\s*\|"  # files (number or "yes")
        r"\s*(\S*)\s*\|"  # fixed (number or empty)
        r"\s*(\S+)\s*\|"  # errors (number or "no")
        r"\s*(\S+)\s*\|"  # warnings (number or "no")
        r"\s*([\d.]+)s\s*\|"  # elapsed time in seconds
    )

    for match in row_pattern.finditer(text):
        descriptor, linter, files, _fixed, errors, warnings, elapsed = match.groups()

        # Parse file count
        try:
            file_count = int(files)
        except ValueError:
            file_count = -1  # "yes" for project-mode linters

        # Parse error/warning counts
        try:
            error_count = int(errors)
        except ValueError:
            error_count = 0  # "no" for project-mode

        try:
            warning_count = int(warnings)
        except ValueError:
            warning_count = 0

        timings.append(
            {
                "linter": linter,
                "descriptor": descriptor,
                "elapsed_s": float(elapsed),
                "files": file_count,
                "errors": error_count,
                "warnings": warning_count,
            }
        )

    return timings


def format_table(timings: list[dict]) -> str:
    """Format timings as a readable table, sorted by elapsed time."""
    sorted_t = sorted(timings, key=lambda x: x["elapsed_s"], reverse=True)
    total = sum(t["elapsed_s"] for t in sorted_t)

    lines = []
    lines.append(f"{'Linter':<25} {'Descriptor':<14} {'Time':>7} {'Files':>6} {'Errors':>7}")
    lines.append("-" * 65)

    for t in sorted_t:
        files_str = str(t["files"]) if t["files"] >= 0 else "repo"
        lines.append(f"{t['linter']:<25} {t['descriptor']:<14} {t['elapsed_s']:>6.2f}s {files_str:>6} {t['errors']:>7}")

    lines.append("-" * 65)
    lines.append(f"{'TOTAL':<25} {'':14} {total:>6.2f}s {len(sorted_t):>6} linters")
    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Extract MegaLinter timing data")
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("megalinter-reports"),
        help="Path to megalinter-reports directory",
    )
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (default: table)",
    )
    args = parser.parse_args()

    report_md = args.report_dir / "megalinter-report.md"
    if not report_md.exists():
        print(f"Report not found: {report_md}", file=sys.stderr)
        sys.exit(1)

    timings = parse_report_markdown(report_md)

    if not timings:
        print("No timing data found in report", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        output = {
            "linters": timings,
            "total_elapsed_s": sum(t["elapsed_s"] for t in timings),
            "linter_count": len(timings),
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_table(timings))


if __name__ == "__main__":
    main()
