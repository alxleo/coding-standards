#!/usr/bin/env python3
"""Bidirectional coverage check between sync-manifest.yml and files on disk.

Every file in configs/, templates/, workflows/, scripts/ must have a manifest
entry, and every manifest entry must have a file on disk.
"""

import sys
from pathlib import Path

import yaml

MANAGED_DIRS = ["configs", "templates", "workflows", "scripts"]
MANIFEST_PATH = Path("sync-manifest.yml")


def main() -> int:
    if not MANIFEST_PATH.exists():
        print(f"ERROR: {MANIFEST_PATH} not found", file=sys.stderr)
        return 1

    with open(MANIFEST_PATH) as f:
        manifest = yaml.safe_load(f)

    # Collect manifest entries as relative paths (dir/filename).
    # Entries with trailing slash (e.g., hooks/) are directory markers — they
    # declare symlink targets but aren't files themselves. Skip them.
    manifest_files: set[str] = set()
    for dir_name in MANAGED_DIRS:
        section = manifest.get(dir_name, {})
        if section:
            for filename in section:
                if filename.endswith("/"):
                    continue  # directory marker, not a file
                manifest_files.add(f"{dir_name}/{filename}")

    # Collect files on disk (recursively to catch subdirectories like scripts/hooks/)
    disk_files: set[str] = set()
    for dir_name in MANAGED_DIRS:
        dir_path = Path(dir_name)
        if dir_path.is_dir():
            for f in dir_path.rglob("*"):
                if f.is_file():
                    disk_files.add(str(f))

    # Compare
    missing_from_manifest = disk_files - manifest_files
    missing_from_disk = manifest_files - disk_files

    ok = True

    if missing_from_manifest:
        ok = False
        print("Files on disk but NOT in sync-manifest.yml:")
        for f in sorted(missing_from_manifest):
            print(f"  {f}")

    if missing_from_disk:
        ok = False
        print("Entries in sync-manifest.yml but NOT on disk:")
        for f in sorted(missing_from_disk):
            print(f"  {f}")

    if ok:
        print(f"sync-manifest.yml: {len(manifest_files)} files, all covered")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
