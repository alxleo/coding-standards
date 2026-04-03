"""Tests for scripts/download_build_assets.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from scripts.download_build_assets import download


class TestDownload:
    def test_download_plain_file(self, tmp_path: Path) -> None:
        dest = tmp_path / "test.json"
        # Mock curl to write a file directly
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = None

            # Simulate what curl does — write to dest
            def side_effect(*args, **kwargs):
                cmd = args[0]
                output_path = cmd[cmd.index("-o") + 1]
                Path(output_path).write_text('{"key": "value"}')

            mock_run.side_effect = side_effect
            result = download("test", "https://example.com/test.json", dest)
            assert "test" in result
            assert str(dest) in result

    def test_download_with_json_normalization(self, tmp_path: Path) -> None:
        dest = tmp_path / "rules.json"

        with patch("subprocess.run") as mock_run:

            def side_effect(*args, **kwargs):
                cmd = args[0]
                output_path = cmd[cmd.index("-o") + 1]
                # Write YAML that needs JSON normalization
                Path(output_path).write_text("rules:\n  - id: test-rule\n")

            mock_run.side_effect = side_effect
            result = download("test", "https://example.com/rules", dest, normalize="json")
            assert "rules" in result
            # Verify the output is valid JSON
            data = json.loads(dest.read_text())
            assert "rules" in data
