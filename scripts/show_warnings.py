#!/usr/bin/env python3
"""Show warnings from the last MegaLinter run, grouped by linter.

Reads megalinter-reports/mega-linter-report.json and extracts findings
from warn-tier linters (those that passed CI but had findings).

Usage:
    show-warnings.py [report-path]
    # default: megalinter-reports/mega-linter-report.json in current dir
"""

import json
import sys
from pathlib import Path


def show_warnings(report_path: Path) -> int:
    if not report_path.exists():
        print("No report found. Run a full lint first.")
        return 1

    report = json.loads(report_path.read_text())
    total = 0

    for linter in report.get("linters", []):
        errors = linter.get("total_number_errors", 0) or 0
        if errors == 0 or linter.get("status") == "error":
            continue

        print(f"\n⚠  {linter['name']} ({errors} warnings)")

        for file_result in linter.get("files_lint_results", []):
            if file_result.get("return_code", 0) != 0:
                print(f"  {file_result.get('file', '?')}")

        stdout = linter.get("lint_result_stdout", "")
        if stdout:
            for line in stdout.split("\n")[:10]:
                if line.strip():
                    print(f"  {line}")

        total += errors

    if total == 0:
        print("No warnings. All clear.")
    else:
        print(f"\n{total} total warnings across warn-tier linters.")
        print("Acknowledge with .repo-standards.yml or fix the findings.")

    return 0


if __name__ == "__main__":
    path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("megalinter-reports/mega-linter-report.json")
    )
    sys.exit(show_warnings(path))
