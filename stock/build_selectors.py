# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Print stock PR selectors from the locked MegaLinter release's source archive."""

import argparse
import json
import sys
import tarfile
from pathlib import Path

import yaml

STOCK = Path(__file__).parent
FIELDS = (
    "file_extensions",
    "file_names_regex",
    "file_names_not_ends_with",
    "files_sub_directory",
    "file_contains_regex",
    "file_contains_regex_extensions",
)


def file_filters(category, key, rules, policy):
    if key == "ACTION_ZIZMOR":
        # The pinned CLI's local workflows/actions collector also honors .gitignore.
        return {
            "file_extensions": [".yml", ".yaml"],
            "file_names_regex": [r"\.gitignore"],
            "include": [r"(^|/)(\.github/workflows/[^/]+\.ya?ml|action\.ya?ml|\.gitignore)$"],
        }
    if category == "REPOSITORY" or rules.get("lint_all_files"):
        return None
    filters = {field: rules[field] for field in FIELDS if rules.get(field)}
    if rules.get("lint_all_other_linters_files") and "file_extensions" not in filters:
        filters["file_extensions"] = ["*"]
    for field in ("FILE_EXTENSIONS", "FILE_NAMES_REGEX"):
        if f"{key}_{field}" in policy:
            filters[field.lower()] = policy[f"{key}_{field}"]
    if include := policy.get(f"{key}_FILTER_REGEX_INCLUDE", policy.get(f"{category}_FILTER_REGEX_INCLUDE")):
        filters["include"] = include if isinstance(include, list) else [include]
    exclude = []
    for prefix in (category, key):
        if pattern := policy.get(f"{prefix}_FILTER_REGEX_EXCLUDE"):
            exclude.extend(pattern if isinstance(pattern, list) else [pattern])
    if exclude:
        filters["exclude"] = exclude
    return filters


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Source archive at the release in stock/images.json")
    args = parser.parse_args()
    lock = json.loads((STOCK / "images.json").read_text())
    policy = yaml.safe_load((STOCK / "mega-linter.yml").read_text())
    selectors = {}
    with tarfile.open(args.archive) as archive:
        for member in archive:
            if "/megalinter/descriptors/" not in member.name or not member.name.endswith(".megalinter-descriptor.yml"):
                continue
            if (stream := archive.extractfile(member)) is None:
                continue
            with stream:
                descriptor = yaml.safe_load(stream)
            category = descriptor["descriptor_id"]
            for linter in descriptor["linters"]:
                key = linter.get("name", f"{category}_{linter['linter_name'].upper().replace('-', '_')}")
                if key in lock["images"]:
                    selectors[key] = file_filters(category, key, {**descriptor, **linter}, policy)
    if selectors.keys() != lock["images"].keys():
        parser.error(f"Missing selectors for {sorted(lock['images'].keys() - selectors.keys())}")
    sys.stdout.write(json.dumps({"version": lock["version"], "selectors": selectors}, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
