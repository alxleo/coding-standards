#!/usr/bin/env python3
# /// script
# requires-python = "==3.13.9"
# dependencies = ["PyYAML==6.0.3"]
# ///
"""Install or run the pinned native MegaLinter profile."""

import argparse
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import yaml


LAUNCHER = "10.2.1-beta202611232244.0"
ENGINE = "10.2.0.post0.dev20261123224600"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "scan"))
    args = parser.parse_args()
    if sys.platform != "linux" or platform.machine() not in ("aarch64", "arm64"):
        parser.error("This profile requires Linux ARM64")

    policy = Path(__file__).with_name("mega-linter.yml")
    linters = yaml.safe_load(policy.read_text())["NATIVE_LINTERS"]
    arguments = ["npx", "--yes", f"mega-linter-runner@{LAUNCHER}", "--release", ENGINE]
    environment = {
        **os.environ,
        "NATIVE_LINTERS": ",".join(linters),
        "NATIVE_INSTALL_RUNTIMES": "auto",
        "NATIVE_ENV_ALLOWLIST": "TRIVY_CACHE_DIR",
        "UV_PYTHON_DOWNLOADS": "never",
    }
    if args.command == "install":
        arguments += ["--install-linters", *linters]
    else:
        environment["NATIVE_MISSING_LINTERS"] = "fail"
        arguments += ["--native"]
    print(f"Native launcher {LAUNCHER}, engine {ENGINE}, platform {platform.machine()}", flush=True)
    start = time.monotonic()
    result = subprocess.run(arguments, env=environment, check=False)
    print(f"MegaLinter native {args.command} seconds: {time.monotonic() - start:.2f}", flush=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
