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

import yaml


def download(name: str, url: str, dest: Path, normalize: str | None = None) -> str:
    """Download a single asset. Returns status message."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    if normalize == "json":
        tmp = dest.with_suffix(".tmp")
        subprocess.run(
            ["curl", "-fsSL", "--compressed", url, "-o", str(tmp)],
            check=True,
            capture_output=True,
        )
        raw = tmp.read_text()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = yaml.safe_load(raw)
        dest.write_text(json.dumps(data))
        tmp.unlink(missing_ok=True)
        rule_count = len(data.get("rules", []))
        return f"  {name} → {dest} ({rule_count} rules)"
    subprocess.run(
        ["curl", "-fsSL", url, "-o", str(dest)],
        check=True,
        capture_output=True,
    )
    return f"  {name} → {dest}"


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
                except subprocess.CalledProcessError:
                    print(f"  FAIL: {futures[future]}")
                    failed += 1

        if failed:
            print(f"ERROR: {failed} download(s) failed in {group_name}")
            sys.exit(1)


if __name__ == "__main__":
    main()
