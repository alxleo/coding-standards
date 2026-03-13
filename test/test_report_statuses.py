"""Tests for scripts/ci/report_statuses.py."""

from __future__ import annotations

import io
from unittest.mock import patch

import report_statuses


def make_env(logdir: str) -> dict[str, str]:
    return {
        "GH_TOKEN": "test-token",
        "SHA": "abc123",
        "API_URL": "https://api.example.com",
        "REPO": "test/repo",
        "RUN_URL": "https://example.com/run/1",
        "RUN_ID": "1",
        "LINT_LOG_DIR": logdir,
    }


def make_mock_api(captured: list | None = None):
    """Create a mock api_request that optionally captures POST calls."""

    def mock_request(url, *, method="GET", data=None):
        if method == "POST":
            if captured is not None:
                captured.append({"url": url, "data": data})
            return {"id": 1}
        return {"jobs": []}

    return mock_request


class TestApiRequest:
    """Tests for the actual HTTP layer — the most likely point of production failure."""

    def test_sets_auth_header(self, tmp_path):
        env = make_env(str(tmp_path))
        with (
            patch.dict("os.environ", env),
            patch("urllib.request.urlopen") as mock_urlopen,
        ):
            mock_resp = io.BytesIO(b'{"ok": true}')
            mock_urlopen.return_value.__enter__ = lambda s: mock_resp
            mock_urlopen.return_value.__exit__ = lambda s, *a: None

            report_statuses.api_request("https://api.example.com/test")

            req = mock_urlopen.call_args[0][0]
            assert req.get_header("Authorization") == "token test-token"
            assert req.get_header("Content-type") == "application/json"

    def test_post_sends_json_body(self, tmp_path):
        env = make_env(str(tmp_path))
        with (
            patch.dict("os.environ", env),
            patch("urllib.request.urlopen") as mock_urlopen,
        ):
            mock_resp = io.BytesIO(b'{"id": 1}')
            mock_urlopen.return_value.__enter__ = lambda s: mock_resp
            mock_urlopen.return_value.__exit__ = lambda s, *a: None

            report_statuses.api_request(
                "https://api.example.com/test",
                method="POST",
                data={"state": "success", "desc": 'has "quotes"'},
            )

            req = mock_urlopen.call_args[0][0]
            assert req.method == "POST"
            body = req.data.decode()
            assert '"success"' in body
            assert r"\"quotes\"" in body  # JSON-escaped

    def test_returns_none_on_network_error(self, tmp_path):
        env = make_env(str(tmp_path))
        with (
            patch.dict("os.environ", env),
            patch(
                "urllib.request.urlopen",
                side_effect=ConnectionError("refused"),
            ),
        ):
            # ConnectionError is a subclass of OSError
            result = report_statuses.api_request("https://api.example.com/test")
            assert result is None

    def test_returns_none_on_invalid_json(self, tmp_path):
        env = make_env(str(tmp_path))
        with (
            patch.dict("os.environ", env),
            patch("urllib.request.urlopen") as mock_urlopen,
        ):
            mock_resp = io.BytesIO(b"<html>502 Bad Gateway</html>")
            mock_urlopen.return_value.__enter__ = lambda s: mock_resp
            mock_urlopen.return_value.__exit__ = lambda s, *a: None

            result = report_statuses.api_request("https://api.example.com/test")
            assert result is None

    def test_passes_timeout(self, tmp_path):
        env = make_env(str(tmp_path))
        with (
            patch.dict("os.environ", env),
            patch("urllib.request.urlopen") as mock_urlopen,
        ):
            mock_resp = io.BytesIO(b'{"ok": true}')
            mock_urlopen.return_value.__enter__ = lambda s: mock_resp
            mock_urlopen.return_value.__exit__ = lambda s, *a: None

            report_statuses.api_request("https://api.example.com/test")

            _, kwargs = mock_urlopen.call_args
            assert kwargs.get("timeout") == 30


class TestPostStatus:
    def test_posts_success_with_correct_url_and_payload(self, tmp_path):
        env = make_env(str(tmp_path))
        captured = []

        with (
            patch.dict("os.environ", env),
            patch.object(
                report_statuses, "api_request", side_effect=make_mock_api(captured)
            ),
            patch.object(report_statuses, "LOGDIR", tmp_path),
        ):
            report_statuses.post_status(
                "python", "success", "python", "Lint: Python (ruff)", {}
            )

        assert len(captured) == 1
        assert (
            captured[0]["url"]
            == "https://api.example.com/repos/test/repo/statuses/abc123"
        )
        assert captured[0]["data"]["state"] == "success"
        assert captured[0]["data"]["context"] == "coding-standards: python"
        assert captured[0]["data"]["description"] == "Passed"

    def test_posts_failure_with_hint_from_log(self, tmp_path):
        env = make_env(str(tmp_path))
        (tmp_path / "yaml.log").write_text("ERROR: bad indentation at line 5\n")
        captured = []

        with (
            patch.dict("os.environ", env),
            patch.object(
                report_statuses, "api_request", side_effect=make_mock_api(captured)
            ),
            patch.object(report_statuses, "LOGDIR", tmp_path),
        ):
            report_statuses.post_status(
                "yaml", "failure", "yaml", "Lint: YAML (yamllint)", {}
            )

        assert captured[0]["data"]["state"] == "failure"
        assert "bad indentation" in captured[0]["data"]["description"]

    def test_failure_without_log_uses_generic_description(self, tmp_path):
        env = make_env(str(tmp_path))
        captured = []

        with (
            patch.dict("os.environ", env),
            patch.object(
                report_statuses, "api_request", side_effect=make_mock_api(captured)
            ),
            patch.object(report_statuses, "LOGDIR", tmp_path),
        ):
            report_statuses.post_status(
                "trivy", "failure", "trivy", "Security: Trivy", {}
            )

        assert captured[0]["data"]["description"] == "Failed"

    def test_skips_non_success_failure_outcomes(self, tmp_path):
        env = make_env(str(tmp_path))
        captured = []

        with (
            patch.dict("os.environ", env),
            patch.object(
                report_statuses, "api_request", side_effect=make_mock_api(captured)
            ),
            patch.object(report_statuses, "LOGDIR", tmp_path),
        ):
            report_statuses.post_status(
                "python", "skipped", "python", "Lint: Python", {}
            )

        assert len(captured) == 0

    def test_uses_step_deep_link_when_available(self, tmp_path):
        env = make_env(str(tmp_path))
        captured = []
        step_urls = {"Lint: Python (ruff)": "https://example.com/job#step:5:1"}

        with (
            patch.dict("os.environ", env),
            patch.object(
                report_statuses, "api_request", side_effect=make_mock_api(captured)
            ),
            patch.object(report_statuses, "LOGDIR", tmp_path),
        ):
            report_statuses.post_status(
                "python", "success", "python", "Lint: Python (ruff)", step_urls
            )

        assert captured[0]["data"]["target_url"] == "https://example.com/job#step:5:1"

    def test_falls_back_to_run_url_without_step_link(self, tmp_path):
        env = make_env(str(tmp_path))
        captured = []

        with (
            patch.dict("os.environ", env),
            patch.object(
                report_statuses, "api_request", side_effect=make_mock_api(captured)
            ),
            patch.object(report_statuses, "LOGDIR", tmp_path),
        ):
            report_statuses.post_status(
                "python", "success", "python", "Lint: Python (ruff)", {}
            )

        assert captured[0]["data"]["target_url"] == "https://example.com/run/1"


class TestGetStepUrls:
    def test_parses_job_response(self, tmp_path):
        env = make_env(str(tmp_path))
        job_response = {
            "jobs": [
                {
                    "name": "Lint",
                    "html_url": "https://example.com/job/1",
                    "steps": [
                        {"name": "Lint: Python (ruff)", "number": 5},
                        {"name": "Lint: YAML (yamllint)", "number": 6},
                    ],
                }
            ]
        }

        with (
            patch.dict("os.environ", env),
            patch.object(report_statuses, "api_request", return_value=job_response),
        ):
            urls = report_statuses.get_step_urls()

        assert urls["Lint: Python (ruff)"] == "https://example.com/job/1#step:5:1"
        assert urls["Lint: YAML (yamllint)"] == "https://example.com/job/1#step:6:1"

    def test_returns_empty_on_api_failure(self, tmp_path):
        env = make_env(str(tmp_path))

        with (
            patch.dict("os.environ", env),
            patch.object(report_statuses, "api_request", return_value=None),
        ):
            urls = report_statuses.get_step_urls()

        assert urls == {}

    def test_returns_empty_when_no_lint_job(self, tmp_path):
        env = make_env(str(tmp_path))

        with (
            patch.dict("os.environ", env),
            patch.object(
                report_statuses,
                "api_request",
                return_value={"jobs": [{"name": "Build", "steps": []}]},
            ),
        ):
            urls = report_statuses.get_step_urls()

        assert urls == {}


class TestMain:
    def test_posts_status_for_every_outcome_file(self, tmp_path):
        """Creates outcome files and verifies each gets a status posted."""
        env = make_env(str(tmp_path))
        # Create outcomes for specific groups
        groups_with_outcomes = {"hygiene": "success", "python": "failure"}
        for logkey, outcome in groups_with_outcomes.items():
            (tmp_path / f"{logkey}.outcome").write_text(outcome)
        (tmp_path / "python.log").write_text("ERROR: bad\n")

        captured = []

        with (
            patch.dict("os.environ", env),
            patch.object(
                report_statuses, "api_request", side_effect=make_mock_api(captured)
            ),
            patch.object(report_statuses, "LOGDIR", tmp_path),
        ):
            report_statuses.main()

        # Verify every outcome file got a status posted
        posted_contexts = {c["data"]["context"] for c in captured}
        assert "coding-standards: file hygiene" in posted_contexts
        assert "coding-standards: python" in posted_contexts
        # Should not post for groups without outcome files
        assert len(captured) == len(groups_with_outcomes)
