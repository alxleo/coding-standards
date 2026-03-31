"""Posts per-group commit statuses to GitHub/Gitea with deep links.

Data-driven: reads outcomes from LINT_LOG_DIR/*.outcome
and group metadata from groups.conf.

Required env vars: GH_TOKEN, SHA, API_URL, REPO, RUN_URL, RUN_ID
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from lint_helpers import extract_hint, parse_groups

SCRIPT_DIR = Path(__file__).resolve().parent
LOGDIR = Path(os.environ.get("LINT_LOG_DIR", "/tmp/lint-results"))


def api_request(url: str, *, method: str = "GET", data: dict | None = None) -> dict | list | None:
    """Make an authenticated API request. Returns parsed JSON or None on failure."""
    headers = {
        "Authorization": f"token {os.environ['GH_TOKEN']}",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(  # nosemgrep: dynamic-urllib-use-detected
            req, timeout=30
        ) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return None


def get_step_urls() -> dict[str, str]:
    """Fetch job metadata and build step_name -> deep_link_url mapping."""
    api_url = os.environ["API_URL"]
    repo = os.environ["REPO"]
    run_id = os.environ["RUN_ID"]

    jobs_data = api_request(f"{api_url}/repos/{repo}/actions/runs/{run_id}/jobs")
    # API may return non-dict on error, or dict without jobs key
    if not isinstance(jobs_data, dict) or not jobs_data.get("jobs"):  # nosemgrep: python-silent-fallback-or
        return {}

    # Find the first job whose name contains "Lint"
    lint_job = next((j for j in jobs_data["jobs"] if "Lint" in j.get("name", "")), None)
    if not lint_job:
        return {}

    job_url = lint_job.get("html_url", "")
    if not job_url:
        return {}

    urls = {}
    for step in lint_job.get("steps", []):
        name = step.get("name", "")
        number = step.get("number")
        if name and number:
            urls[name] = f"{job_url}#step:{number}:1"

    return urls


def post_status(
    context: str,
    outcome: str,
    logkey: str,
    step_name: str,
    step_urls: dict[str, str],
) -> None:
    """Post a single commit status."""
    if outcome not in ("success", "failure"):
        return

    state = outcome
    # nosemgrep: python-silent-fallback-or
    description = "Passed" if outcome == "success" else (extract_hint(LOGDIR / f"{logkey}.log") or "Failed")

    target_url = step_urls.get(step_name, os.environ["RUN_URL"])

    payload = {
        "state": state,
        "context": f"coding-standards: {context}",
        "description": description,
        "target_url": target_url,
    }

    api_url = os.environ["API_URL"]
    repo = os.environ["REPO"]
    sha = os.environ["SHA"]

    result = api_request(
        f"{api_url}/repos/{repo}/statuses/{sha}",
        method="POST",
        data=payload,
    )

    status_msg = "OK" if result else "FAILED"
    ctx = payload["context"]
    print(f"  Posted status: {ctx} -> {state} ({description}) [{status_msg}]")


def main() -> None:
    step_urls = get_step_urls()
    groups = parse_groups(SCRIPT_DIR / "groups.conf")

    for logkey, _display_name, status_context, step_name in groups:
        outcome_file = LOGDIR / f"{logkey}.outcome"
        if outcome_file.exists():
            outcome = outcome_file.read_text().strip()
            post_status(status_context, outcome, logkey, step_name, step_urls)


if __name__ == "__main__":
    main()
