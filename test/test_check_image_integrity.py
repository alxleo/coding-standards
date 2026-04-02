"""Tests for scripts/hooks/check-image-integrity.

Runs the hook as a subprocess and checks exit codes + output.
The hook validates invariants across Dockerfile, config, plugins, etc.
"""

from __future__ import annotations

import subprocess


class TestImageIntegrity:
    def test_passes_on_current_repo(self) -> None:
        """The hook should pass on the current (known-good) repo state."""
        result = subprocess.run(
            ["python3", "scripts/hooks/check-image-integrity"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"Integrity check failed:\n{result.stdout}"

    def test_output_has_no_errors(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/hooks/check-image-integrity"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert "✗" not in result.stdout, f"Found errors:\n{result.stdout}"
