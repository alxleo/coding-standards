#!/usr/bin/env python3
"""Download build-time assets declared in build-assets.yml.

Replaces download-schemas.sh and download-semgrep-rules.sh with one
data-driven script. Downloads happen in parallel. YAML→JSON normalization
for semgrep rules (json.loads is 381x faster than ruamel.yaml at runtime).

Usage:
    python3 scripts/download_build_assets.py [--config build-assets.yml]
"""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml


def download(name: str, url: str, dest: Path, normalize: str | None = None) -> str:
    """Download a single asset. Returns status message."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    status = f"  {name} → {dest}"
    with TemporaryDirectory(dir=dest.parent) as staging_dir:
        staged = Path(staging_dir) / dest.name
        flags = ["-fsSL", "--compressed"] if normalize == "json" else ["-fsSL"]
        subprocess.run(
            ["curl", *flags, url, "-o", str(staged)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        if normalize == "json":
            raw = staged.read_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = yaml.safe_load(raw)
            staged.write_text(json.dumps(data))
            status = f"{status} ({len(data.get('rules', []))} rules)"
        staged.replace(dest)
    return status


def main() -> None:
    config_path = Path("build-assets.yml")
    for arg in sys.argv[1:]:
        if arg == "--config":
            continue
        config_path = Path(arg)

    if not config_path.exists():
        # Inside Docker, config is at /opt/coding-standards/
        alt = Path("/opt/coding-standards") / config_path.name
        if alt.exists():
            config_path = alt

    config = yaml.safe_load(config_path.read_text())

    for group_name, group in config.items():
        dest_dir = Path(group["dest"])
        normalize = group.get("normalize")
        items = group.get("items", {})
        ext = ".json"

        print(f"Downloading {group_name} ({len(items)} items):")

        futures = {}
        with ThreadPoolExecutor(max_workers=16) as pool:
            for name, url in items.items():
                dest = dest_dir / f"{name}{ext}"
                future = pool.submit(download, name, url, dest, normalize)
                futures[future] = name

            failed = 0
            for future in as_completed(futures):
                try:
                    print(future.result())
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                    print(f"  FAIL: {futures[future]} ({type(exc).__name__})")
                    failed += 1

        if failed:
            print(f"ERROR: {failed} download(s) failed in {group_name}")
            sys.exit(1)


if __name__ == "__main__":
    main()
