"""Read the Dockerfile declarations used as the per-linter image lock."""

import re
from pathlib import Path

LOCK = Path(__file__).with_name("Dockerfile.images")


def image_pins():
    images = {}
    versions = set()
    for line in LOCK.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        pin = re.fullmatch(
            r"FROM ghcr\.io/oxsecurity/megalinter-only-([a-z0-9_]+):(v[\d.]+)@(sha256:[0-9a-f]{64})", line
        )
        if not pin or pin[1].upper() in images:
            message = f"Invalid or duplicate stock image pin: {line}"
            raise ValueError(message)
        key, version, digest = pin.groups()
        images[key.upper()] = digest
        versions.add(version)
    if len(versions) != 1:
        message = "Stock image pins must share one MegaLinter release"
        raise ValueError(message)
    return {"version": versions.pop(), "images": images}
