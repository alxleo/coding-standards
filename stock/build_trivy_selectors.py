# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Generate PR file patterns from the Trivy release in the pinned linter image."""

import argparse
import json
import re
import sys
from pathlib import Path

from image_pins import image_pins


def rows(path):
    for line in path.read_text().splitlines():
        if line.startswith("|"):
            yield [field.strip() for field in line.strip("|").split("|")]


def go_strings(text, pattern):
    match = re.search(pattern, text)
    if match is None:
        message = f"Trivy source no longer matches {pattern}"
        raise ValueError(message)
    return re.findall(r'"([^\"]+)"', match[1])


def patterns(source):
    docs = source / "docs/guide/coverage"
    language = (re.sub(r"\[\^\d+\]", "", row[1]) for row in rows(docs / "language/index.md") if row[4] == "✅")
    names = {f"*{name}" if name.startswith(".") else name for name in language}
    names.update(
        name.replace(r"\*", "*")
        for row in rows(docs / "iac/index.md")
        if row[0].startswith("[")
        for name in row[1].split(", ")
        if name not in {"etc.", "without extension"}
    )

    # The coverage table omits some native analyzers and their companion files.
    constants = (source / "pkg/fanal/types/const.go").read_text()
    for key in ("GoSum", "CargoToml", "PyLockFile", "PyProject"):
        names.update(go_strings(constants, rf'(?m)^\s*{key}\s*=\s*("[^\"]+")'))
    node = (source / "pkg/fanal/analyzer/language/nodejs/pkg/pkg.go").read_text()
    names.update(go_strings(node, r'requiredFile = ("[^\"]+")'))  # Yarn reads this manifest too.
    names.add("pylock.*.toml")  # PEP 751 names accepted by pylock.matchLockFile.
    config = source / "pkg/fanal/analyzer/config"
    docker = go_strings((config / "dockerfile/docker.go").read_text(), r"requiredFiles = \[\]string\{([^}]+)\}")
    helm = (config / "helm/helm.go").read_text()
    names.update(f"*{ext}" for ext in go_strings(helm, r"acceptedExts = \[\]string\{([^}]+)\}"))
    names.update(go_strings(helm, r"range \[\]string\{([^}]+)\}"))
    ansible = (config / "ansible/ansible.go").read_text()
    names.update(go_strings(ansible, r"filepath\.Base\(filePath\) == (\"[^\"]+\")"))
    detection = (source / "pkg/iac/detection/detect.go").read_text().split("func IsTerraformFile", 1)[1]
    names.update(f"*{ext}" for ext in go_strings(detection, r"range \[\]string\{([^}]+)\}"))
    return sorted(name for name in names - set(docker)), sorted(name.lower() for name in docker)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Unpacked Trivy release source")
    parser.add_argument("version", help="Trivy version reported by the pinned image")
    args = parser.parse_args()
    files, docker = patterns(args.source)
    lock = image_pins()["images"]
    result = {"version": args.version, "image": lock["REPOSITORY_TRIVY"], "files": files, "docker": docker}
    sys.stdout.write(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
