#!/usr/bin/env python3
"""Read MegaLinter JSON report, post per-linter commit statuses.

Works with both Gitea and GitHub APIs (same endpoint shape).

Usage:
  python3 megalinter_report_statuses.py [report-path]

Environment variables:
  GITEA_URL / GITHUB_API_URL  — API base URL
  GITEA_TOKEN / GITHUB_TOKEN  — auth token
  GITHUB_REPOSITORY           — owner/repo
  GITHUB_SHA                   — commit SHA
  GITHUB_RUN_ID               — workflow run ID (for target_url)
  GITHUB_SERVER_URL            — server URL (for target_url)
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

_DEFAULT_REPORT = "megalinter-reports/mega-linter-report.json"


def main() -> None:
    report_path = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_REPORT

    with Path(report_path).open() as f:
        report = json.load(f)

    # Detect platform
    gitea_url = os.environ.get("GITEA_URL", "")
    github_api = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    # Gitea token takes precedence; fall back to GitHub token
    token = os.environ.get("GITEA_TOKEN") or os.environ.get(  # nosemgrep: coding-standards.python-silent-fallback-or
        "GITHUB_TOKEN", ""
    )
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    sha = os.environ.get("GITHUB_SHA", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")

    # All three are required to post commit statuses
    if not token or not repo or not sha:  # nosemgrep: coding-standards.python-silent-fallback-or
        print("Missing GITEA_TOKEN/GITHUB_TOKEN, GITHUB_REPOSITORY, or GITHUB_SHA")
        sys.exit(1)

    # Build status API URL
    if gitea_url:
        api_url = f"{gitea_url}/api/v1/repos/{repo}/statuses/{sha}"
    else:
        api_url = f"{github_api}/repos/{repo}/statuses/{sha}"

    target_url = f"{server_url}/{repo}/actions/runs/{run_id}" if run_id else ""

    posted = 0
    for linter in report.get("linters", []):
        if not linter.get("is_active", True):
            continue

        state = "success" if linter["return_code"] == 0 else "failure"
        errors = linter.get("total_number_errors", 0)
        warnings = linter.get("total_number_warnings", 0)
        elapsed = linter.get("elapsed_time_s", 0)

        if state == "failure":
            desc = f"{errors} error(s) ({elapsed:.1f}s)"
        elif warnings > 0:
            desc = f"{warnings} warning(s) ({elapsed:.1f}s)"
        else:
            desc = f"No issues ({elapsed:.1f}s)"

        context = f"coding-standards: {linter['linter_name']}"

        payload = json.dumps(
            {
                "state": state,
                "target_url": target_url,
                "description": desc[:140],
                "context": context,
            }
        ).encode()

        req = urllib.request.Request(
            api_url,
            data=payload,
            headers={
                "Authorization": f"token {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            # nosemgrep: dynamic-urllib-use-detected
            with urllib.request.urlopen(req) as resp:
                status_code = resp.status
        except urllib.error.HTTPError as e:
            status_code = e.code
        except urllib.error.URLError as e:
            print(f"  ⚠ {context}: connection error: {e.reason}")
            status_code = 0

        icon = "✅" if state == "success" else "❌"
        print(f"  {icon} {context:45s} {state:8s} → HTTP {status_code}")
        posted += 1

    print(f"\nPosted {posted} commit statuses to {api_url.split('/statuses')[0]}")


if __name__ == "__main__":
    main()
