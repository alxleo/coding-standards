"""Prints the coding-standards summary table and writes GitHub Step Summary.

Data-driven: reads outcomes from LINT_LOG_DIR/*.outcome
and group metadata from groups.conf.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from lint_helpers import extract_errors, parse_groups

SCRIPT_DIR = Path(__file__).resolve().parent
LOGDIR = Path(os.environ.get("LINT_LOG_DIR", "/tmp/lint-results"))


def main() -> None:
    groups = parse_groups(SCRIPT_DIR / "groups.conf")
    failed = False
    summary_rows: list[str] = []

    print()
    print("\u2554" + "\u2550" * 38 + "\u2557")
    print("\u2551       coding-standards summary       \u2551")
    print("\u2560" + "\u2550" * 38 + "\u2563")

    for logkey, display_name, _status_context, _step_name in groups:
        outcome_file = LOGDIR / f"{logkey}.outcome"
        outcome = "skipped"
        if outcome_file.exists():
            outcome = outcome_file.read_text().strip()

        if outcome == "success":
            print(f"\u2551  {display_name:<28}  pass  \u2551")
        elif outcome == "failure":
            print(f"\u2551  {display_name:<28}  FAIL  \u2551")
            failed = True
            errors = extract_errors(LOGDIR / f"{logkey}.log")
            if errors:
                detail = errors[0][:120]
                summary_rows.append(f"| :x: FAIL | **{display_name}** | `{detail}` |")
                for line in errors:
                    print(f"\u2551    \u21b3 {line}")
            else:
                summary_rows.append(f"| :x: FAIL | **{display_name}** | \u2014 |")
        elif outcome == "skipped":
            print(f"\u2551  {display_name:<28}  skip  \u2551")
        else:
            print(f"\u2551  {display_name:<28}  ----  \u2551")

    print("\u255a" + "\u2550" * 38 + "\u255d")
    print()

    # Write GitHub Step Summary
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if summary_path:
        with open(summary_path, "a") as f:
            if failed:
                f.write("### :x: coding-standards \u2014 failures detected\n\n")
                f.write("| Status | Check | Detail |\n")
                f.write("|--------|-------|--------|\n")
                for row in summary_rows:
                    f.write(row + "\n")
                f.write("\n")

                # Write error details per group
                for logfile in sorted(LOGDIR.glob("*.log")):
                    errors = extract_errors(logfile)
                    if errors:
                        f.write(
                            f"<details><summary><b>{logfile.stem}</b> errors</summary>\n\n"
                        )
                        f.write("```\n")
                        for line in errors:
                            f.write(line + "\n")
                        f.write("```\n</details>\n\n")
            else:
                f.write(
                    "### :white_check_mark: coding-standards \u2014 all checks passed\n"
                )

    if failed:
        print("One or more linter groups failed. See details above.")
        sys.exit(1)

    print("All checks passed.")


if __name__ == "__main__":
    main()
