# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Run the pinned MegaLinter images on one checkout."""

import argparse
import concurrent.futures
import fcntl
import json
import logging
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import NamedTuple

from image_pins import LOCK, image_pins

IMAGE_PREFIX = "coding-standards-stock-owned/"
REGISTRY = "ghcr.io"
REPORT = "summary.md"
ZIZMOR_NO_INPUTS = 3
SCHEMA_MOUNT = Path("/opt/coding-standards/schemas")
V8R_IGNORE = "/opt/coding-standards/configs/.v8rignore"
SOURCE = "/tmp/lint"  # noqa: S108 - reserved image workspace, mounted by Docker
POLICY = "/tmp/policy"  # noqa: S108 - read-only mount next to workspace
LOGGER = logging.getLogger(__name__)
ARCH = {"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64"}.get(platform.machine())
CURRENT_KEYS = {
    "ACTION_ZIZMOR": "REPOSITORY_ZIZMOR",
    "REPOSITORY_BETTERLEAKS": "REPOSITORY_BETTERLEAKS_GIT",
}


class ConsumerPolicy(NamedTuple):
    blocking: set[str]
    configs: dict[str, Path | None]
    semgrep: list[str]


def command(*args, cwd=None, check=True):
    return subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)  # noqa: S603


def docker(*args, check=True):
    return command("docker", *args, check=check)


def inspect(ref):
    result = docker("image", "inspect", ref, check=False)
    return json.loads(result.stdout)[0] if result.returncode == 0 else None


def require_image(ref):
    if image := inspect(ref):
        return image
    message = f"Docker image is missing after pull: {ref}"
    raise RuntimeError(message)


def fetch(host, path, headers=None, *, follow_redirects=False):
    options = []
    for key, value in (headers or {}).items():
        options += ["--header", f"{key}: {value}"]
    return command(
        "curl",
        "--disable",
        "--silent",
        "--show-error",
        "--fail",
        "--proto",
        "=https",
        *(["--location", "--proto-redir", "=https"] if follow_redirects else []),
        "--max-time",
        "60",
        *options,
        f"https://{host}{path}",
    ).stdout


def manifest(repo, digest):
    query = urllib.parse.urlencode({"scope": f"repository:{repo}:pull"})
    token = json.loads(fetch(REGISTRY, f"/token?{query}"))["token"]
    body = fetch(
        REGISTRY,
        f"/v2/{repo}/manifests/{digest}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": (
                "application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json, "
                "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json"
            ),
        },
    )
    return json.loads(body)


def pull(ref):
    start = time.monotonic()
    result = docker("pull", ref, check=False)
    LOGGER.info("%s", result.stdout.rstrip())
    if result.returncode:
        message = f"Docker pull failed for {ref}"
        raise RuntimeError(message)
    downloaded = set(re.findall(r"^([0-9a-f]+): Download complete", result.stdout, re.MULTILINE))
    layer_bytes = 0
    if downloaded:
        repo, digest = ref.removeprefix("ghcr.io/").split("@", 1)
        image_manifest = manifest(repo, digest)
        if "manifests" in image_manifest:
            platform_digest = next(
                item["digest"]
                for item in image_manifest["manifests"]
                if item["platform"]["os"] == "linux" and item["platform"]["architecture"] == ARCH
            )
            image_manifest = manifest(repo, platform_digest)
        layers = image_manifest["layers"]
        layer_bytes = sum(
            layer["size"] for layer in layers if layer["digest"].removeprefix("sha256:")[:12] in downloaded
        )
    elif "Downloaded newer image" in result.stdout and "Already exists" not in result.stdout:
        layer_bytes = None
    return layer_bytes, round(time.monotonic() - start, 2)


def image_for(key, digest):
    ref = f"ghcr.io/oxsecurity/megalinter-only-{key.lower()}@{digest}"
    owned = f"{IMAGE_PREFIX}{key.lower()}:{digest.removeprefix('sha256:')}"
    if image := inspect(owned):
        return owned, image, 0, 0
    if image := inspect(ref):
        return ref, image, 0, 0
    size, elapsed = pull(ref)
    docker("image", "tag", ref, owned)
    # Only the reference added by this pull is untagged. The owned tag retains the image.
    result = docker("image", "rm", ref, check=False)
    if result.returncode:
        LOGGER.info("%s", result.stdout.rstrip())
    return owned, require_image(owned), size, elapsed


def remove_stale(lock, cache):
    # Tags from a job using an older policy are safe to delete after its host lock is released.
    # Docker keeps layers referenced by any other tags or containers.
    tags = docker(
        "image", "ls", "--format", "{{.Repository}}:{{.Tag}}", "--filter", f"reference={IMAGE_PREFIX}*"
    ).stdout.splitlines()
    for tag in tags:
        match = re.fullmatch(r"coding-standards-stock-owned/([a-z0-9_]+):([0-9a-f]{64})", tag)
        if match and f"sha256:{match[2]}" != lock.get(match[1].upper()):
            result = docker("image", "rm", tag, check=False)
            LOGGER.info("%s", result.stdout.rstrip())
    for kind, key in (("semgrep", "REPOSITORY_SEMGREP"),):
        current = lock[key].removeprefix("sha256:")
        for entry in cache.glob(f"{kind}-*"):
            suffix = entry.name.removeprefix(f"{kind}-")
            if (
                re.fullmatch("[0-9a-f]{64}", suffix)
                and suffix != current
                and not entry.is_symlink()
                and (entry / ".stock-owned").is_file()
            ):
                shutil.rmtree(entry)


def packs(directory, consumer):
    names = ("security-audit", "trailofbits")
    paths = []
    for name in names:
        path = directory / f"{name}.yaml"
        if not path.is_file():
            body = fetch("semgrep.dev", f"/c/p/{name}")
            temporary = path.with_suffix(".partial")
            temporary.write_text(body)
            temporary.replace(path)
            LOGGER.info("Semgrep pack %s downloaded bytes: %s", name, len(body))
        if consumer:
            # The existing image parses pre-normalized JSON. Cache that same format.
            import yaml  # noqa: PLC0415 - only the opt-in uv entry point needs PyYAML

            normalized = path.with_suffix(".json")
            if not normalized.is_file():
                temporary = normalized.with_suffix(".partial")
                temporary.write_text(json.dumps(yaml.safe_load(path.read_text())))
                temporary.replace(normalized)
            path = normalized
        paths.append(path)
    return paths


def mount(path, target, *, writable=False):
    return ["--mount", f"type=bind,src={path},dst={target}" + ("" if writable else ",readonly")]


def checkout_file(source, selection):
    path = source / selection
    if selection.is_absolute() or not path.resolve().is_relative_to(source) or not path.is_file():
        message = f"Expected a file inside the checkout: {selection}"
        raise ValueError(message)
    return path.resolve().relative_to(source)


def consumer_configs(source, policy, enabled):
    defaults = {
        "PYTHON_RUFF": ("ruff.toml", ".ruff.toml"),
        "YAML_YAMLLINT": (".yamllint", ".yamllint.yml", ".yamllint.yaml"),
        "JSON_V8R": (".v8rrc.yml", ".v8rrc.yaml", ".v8rrc.json"),
        "YAML_V8R": (".v8rrc.yml", ".v8rrc.yaml", ".v8rrc.json"),
    }
    configs = {}
    for key in enabled.intersection(defaults):
        filename = policy.get(f"{key}_CONFIG_FILE")
        if filename == "LINTER_DEFAULT":
            configs[key] = None
            continue
        directory = Path(policy.get(f"{key}_RULES_PATH", policy.get("LINTER_RULES_PATH", ".")))
        names = [Path(filename)] if filename is not None else list(map(Path, defaults[key]))
        paths = [directory / name for name in names] + names
        found = next((path for path in paths if (source / path).is_file()), None)
        if found is not None or filename is not None:
            configs[key] = checkout_file(source, found if found is not None else paths[0])
    return configs


def consumer_policy(source, filename):
    import yaml  # noqa: PLC0415 - only the opt-in uv entry point needs PyYAML

    policy = yaml.safe_load((source / checkout_file(source, filename)).read_text())
    # Consume only the declared policy fields. Never run the legacy PRE/POST commands.
    enabled = set(policy["ENABLE_LINTERS"])
    advisory = set(policy.get("DISABLE_ERRORS_LINTERS", ()))
    arguments = policy.get("REPOSITORY_SEMGREP_ARGUMENTS", "")
    if isinstance(arguments, str):
        arguments = shlex.split(arguments)
    arguments = iter(arguments)
    semgrep = []
    for argument in arguments:
        if argument == "--baseline-commit":
            next(arguments)
        elif not argument.startswith("--baseline-commit="):
            semgrep.append(argument)
    return ConsumerPolicy(enabled - advisory, consumer_configs(source, policy, enabled), ["--metrics=off", *semgrep])


def consumer_environment(consumer, key):
    if not consumer or key not in consumer.configs:
        return {}
    config = consumer.configs[key]
    env = {f"{key}_CONFIG_FILE": config.name if config else "LINTER_DEFAULT", "DISABLE_ERRORS_LINTERS": ""}
    if config:
        env[f"{key}_RULES_PATH"] = f"{SOURCE}/{config.parent}"
    return env


def legacy_v8r_mounts(source, config, cache, policy):
    """Supply the bundled paths used by existing v8r catalogs."""
    import yaml  # noqa: PLC0415 - the consumer policy uses the same optional dependency

    content = (source / config).read_text()
    options = []
    if f"{SCHEMA_MOUNT}/" in content:
        assets = yaml.safe_load((policy / "build-assets.yml").read_text())["schemas"]["items"]
        directory = cache / "schema-assets"
        for name, url in assets.items():
            path = directory / f"{name}.json"
            target = SCHEMA_MOUNT / path.name
            if str(target) not in content:
                continue
            if not path.is_file():
                directory.mkdir(exist_ok=True)
                uri = urllib.parse.urlsplit(url)
                with tempfile.TemporaryDirectory(dir=directory) as staging:
                    staged = Path(staging) / path.name
                    staged.write_text(fetch(uri.netloc, uri.path, follow_redirects=True))
                    staged.replace(path)
            options += mount(path, target)
    if V8R_IGNORE in content:
        options += mount(policy / "lint-configs/.v8rignore", V8R_IGNORE)
    return options


def semgrep_setup(args, digest, source, policy):
    directory = args.cache / f"semgrep-{digest.removeprefix('sha256:')}"
    if not directory.exists():
        directory.mkdir()
        (directory / ".stock-owned").touch()
    options = mount(policy / "semgrep-rules", "/rules/custom")
    rulesets = ["/rules/custom"]
    for path in packs(directory, args.consumer is not None):
        target = f"/rules/{path.name}"
        rulesets.append(target)
        options += mount(path, target)
    env = {"SEMGREP_ENABLE_VERSION_CHECK": "0"}
    if args.consumer:
        env["REPOSITORY_SEMGREP_ARGUMENTS"] = shlex.join(args.consumer.semgrep)
        if (source / ".semgrep").is_dir():
            rulesets.append(f"{SOURCE}/.semgrep")
    env["REPOSITORY_SEMGREP_RULESETS"] = ",".join(rulesets)
    if args.base:
        env["SEMGREP_BASELINE_COMMIT"] = args.base
        if not args.rootless:
            # A rootless daemon already maps container root to the runner.
            # With a rootful daemon, match the runner to keep the clone removable.
            options += ["--user", f"{os.getuid()}:{os.getgid()}"]
            env["HOME"] = "/tmp"  # noqa: S108 - private to the lint container
    return [*options, "--network", "none"], env


def run_scanner(options, command_line):
    return docker(
        "run",
        "--rm",
        "--pull=never",
        "--label",
        "io.coding-standards.stock=true",
        "--security-opt=no-new-privileges",
        "--workdir",
        SOURCE,
        *options,
        *command_line,
        check=False,
    )


def scoped_semgrep_paths(args):
    if args.semgrep_pr_scope == "full" or not (args.base and args.consumer and args.semgrep_targets):
        return None
    scope_files = {".gitattributes", ".gitignore", ".gitmodules", ".semgrepignore"}
    if any(path == args.semgrep_config or path.name in scope_files for path in map(Path, args.diff)):
        return None
    import yaml  # noqa: PLC0415 - the consumer policy uses the same optional dependency

    config = yaml.safe_load((args.source / args.semgrep_config).read_text())
    rules = config.get("rules", []) if isinstance(config, dict) else []
    if not rules or any(
        not isinstance(rule, dict)
        or rule.get("mode", "search") != "search"
        or rule.get("options", {}).get("interfile")
        or {"project-depends-on", "r2c-internal-project-depends-on"}.intersection(rule)
        for rule in rules
    ):
        return None
    return args.changed_files


def scan_semgrep_rules(image_task, args):
    """Run the configured local rules with Semgrep's CLI."""
    key = "REPOSITORY_SEMGREP_LOCAL"
    reports = args.reports / key.lower()
    reports.mkdir(parents=True, exist_ok=True)
    report = reports / "findings.json"
    report.unlink(missing_ok=True)
    targets = []
    if args.semgrep_targets:
        inventory = command("git", "ls-files", "-z", "--", *args.semgrep_targets, cwd=args.source)
        targets = inventory.stdout.rstrip("\0").split("\0") if inventory.stdout else []
        if not targets:
            message = "Semgrep target pathspecs matched no tracked files"
            raise ValueError(message)

    paths = scoped_semgrep_paths(args)
    include = []
    if paths:
        # Keep Semgrep's normal ignore rules for changed files. Only explicit
        # targets should bypass its default test exclusions.
        for path in (*paths, *targets):
            pattern = re.sub(r"([\\*?\[\]])", r"\\\1", path)
            include.append(f"--include=/{pattern}")
        if sum(len(os.fsencode(option)) + 1 for option in include) > 32 * 1024:
            include = []
            paths = None
    LOGGER.info("Semgrep local scope: %s", "changed files and explicit targets" if paths is not None else "full tree")
    ref, image, _, _ = image_task.result()
    options = [
        *mount(args.source, SOURCE),
        *mount(reports, "/stock-reports", writable=True),
        "--network",
        "none",
        "--entrypoint",
        "semgrep",
        "--env",
        "GIT_CONFIG_COUNT=1",
        "--env",
        "GIT_CONFIG_KEY_0=safe.directory",
        "--env",
        f"GIT_CONFIG_VALUE_0={SOURCE}",
    ]
    command_line = [
        ref,
        "scan",
        "--strict",
        "--metrics=off",
        "--disable-version-check",
        *([] if args.advisory else ["--error"]),
        "--config",
        f"{SOURCE}/{args.semgrep_config}",
        "--json-output=/stock-reports/findings.json",
        *include,
        "--",
        *(["."] if paths is None or paths else []),
        *(f"./{path}" for path in targets),
    ]
    start = time.monotonic()
    proc = run_scanner(options, command_line)
    elapsed = round(time.monotonic() - start, 2)
    (reports / "console.log").write_text(proc.stdout)
    findings = json.loads(report.read_text()) if report.is_file() else {}
    scanned = findings.get("paths", {}).get("scanned", [])
    missing = set(targets).difference(scanned)
    if missing:
        LOGGER.error("%s did not scan %d explicit targets: %s", key, len(missing), sorted(missing)[:20])
    errors = findings.get("errors", [])
    status = proc.returncode
    if status == 0 and (not findings or errors or missing):
        status = 1
    LOGGER.info(
        "%s scanned %d files, including %d/%d explicit targets, and reported %d findings",
        key,
        len(scanned),
        len(targets) - len(missing),
        len(targets),
        len(findings.get("results", [])),
    )
    if status:
        LOGGER.info("%s:\n%s", key, proc.stdout[-12000:])
    return {
        "linter": key,
        "started_seconds": round(start - args.started, 2),
        "seconds": elapsed,
        "scanner_seconds": elapsed,
        "exit": status,
        "pull_seconds": 0,
        "registry_layer_bytes": 0,
        "image_id": image["Id"],
        "image_bytes": image["Size"],
    }


def scan_one(key, digest, args, source, image_task):
    reports, base, advisory = args.reports, args.base, args.advisory
    if args.consumer:
        blocking = args.consumer.blocking
        advisory = advisory or (key not in blocking and CURRENT_KEYS.get(key) not in blocking)
    policy = LOCK.parent.parent.resolve()
    image_ref, image, registry_bytes, pull_seconds = image_task.result() if image_task else image_for(key, digest)
    report_dir = reports / key.lower()
    report_dir.mkdir(parents=True, exist_ok=True)
    options = [
        *mount(source, SOURCE, writable=bool(base and key == "REPOSITORY_SEMGREP")),
        *mount(policy, POLICY),
        *mount(report_dir, "/stock-reports", writable=True),
    ]
    env = {
        "DEFAULT_WORKSPACE": SOURCE,
        "GITHUB_WORKSPACE": SOURCE,
        "REPORT_OUTPUT_FOLDER": "/stock-reports",
        "MEGALINTER_CONFIG": "stock.mega-linter.yml",
        "EXTENDS": "../policy/stock/mega-linter.yml",
        "ENABLE_LINTERS": key,
        "VALIDATE_ALL_CODEBASE": "false" if base else "true",
        "DISABLE_ERRORS": str(advisory).lower(),
        "APPLY_FIXES": "none",
        "MARKDOWN_SUMMARY_REPORTER_FILE_NAME": REPORT,
        "PRINT_ALPACA": "false",
        "DEFAULT_BRANCH": "stock-scan-base" if base else "HEAD",
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": "safe.directory",
        "GIT_CONFIG_VALUE_0": SOURCE,
        "GIT_CONFIG_KEY_1": "core.autocrlf",
        "GIT_CONFIG_VALUE_1": "false",
    }
    if key == "PYTHON_RUFF":
        env["RUFF_CACHE_DIR"] = "/tmp/ruff-cache"  # noqa: S108 - private to the lint container
    env.update(consumer_environment(args.consumer, key))
    if key.endswith("_V8R") and args.consumer and (config := args.consumer.configs.get(key)):
        options += legacy_v8r_mounts(source, config, args.cache, policy)
    if key == "REPOSITORY_SEMGREP":
        data_mount, semgrep_env = semgrep_setup(args, digest, source, policy)
        options += data_mount
        env.update(semgrep_env)
    command_line = [image_ref]
    if key == "REPOSITORY_BETTERLEAKS" and base:
        # The pinned adapter adds a caret to the base and scans one extra commit.
        env.update(
            REPOSITORY_BETTERLEAKS_PR_COMMITS_SCAN="false",
            REPOSITORY_BETTERLEAKS_COMMAND_REMOVE_ARGUMENTS="dir",
            REPOSITORY_BETTERLEAKS_ARGUMENTS=f'git "--log-opts=--no-merges {base}..HEAD"',
        )
    if key == "ACTION_ZIZMOR":
        options += ["--entrypoint", "zizmor", "--network", "none"]
        command_line += [
            "--offline",
            "--quiet",
            "--collect",
            "workflows,actions",
            "--strict-collection",
            "--format=json-v1",
            *(["--no-exit-codes"] if advisory else []),
            "--config",
            f"{POLICY}/lint-configs/.zizmor.yml",
            ".",
        ]
    for name, value in env.items():
        options += ["--env", f"{name}={value}"]

    start = time.monotonic()
    proc = run_scanner(options, command_line)
    (report_dir / "console.log").write_text(proc.stdout)
    elapsed = round(time.monotonic() - start, 2)
    status = proc.returncode
    if key == "ACTION_ZIZMOR" and status == ZIZMOR_NO_INPUTS and "error: no inputs collected" in proc.stdout:
        status = 0
    if proc.returncode or key == "ACTION_ZIZMOR":
        LOGGER.info("%s:\n%s", key, proc.stdout[-12000:])
    engine_report = report_dir / "mega-linter-report.json"
    scanned = json.loads(engine_report.read_text())["active_linters"] if engine_report.is_file() else []
    scanner_seconds = elapsed if key == "ACTION_ZIZMOR" else None
    if scanned:
        scanner_seconds = round(sum(linter["elapsed_time_s"] for linter in scanned), 2)
    return {
        "linter": key,
        "started_seconds": round(start - args.started, 2),
        "seconds": elapsed,
        "scanner_seconds": scanner_seconds,
        "exit": status,
        "pull_seconds": pull_seconds,
        "registry_layer_bytes": registry_bytes,
        "image_id": image["Id"],
        "image_bytes": image["Size"],
    }


def summary(results, reports):
    text = ["### Stock lint", "", "| Linter | Result | Seconds |", "| --- | --- | ---: |"]
    for item in results:
        key = item["linter"]
        text.append(f"| {key} | {'exit ' + str(item['exit']) if item['exit'] else 'ok'} | {item['seconds']} |")
    for item in results:
        report = reports / item["linter"].lower() / REPORT
        if report.is_file():
            text.extend(
                (
                    "",
                    "<details>",
                    f"<summary>{item['linter']}</summary>",
                    "",
                    report.read_text()[:12000],
                    "",
                    "</details>",
                )
            )
    if target := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(target).open("a") as file:
            file.write("\n".join(text) + "\n")


def selected_file(source, name, rules):
    if not name.startswith(rules.get("files_sub_directory", "")):
        return False
    path = Path(name)
    extension = path.suffix
    extensions = rules.get("file_extensions", ())
    if (
        extension not in extensions
        and "*" not in extensions
        and not re.fullmatch("|".join(rules.get("file_names_regex", ())), path.name)
    ):
        return False
    locations = (name, f"{SOURCE}/{name}")
    include = rules.get("include")
    if (
        name.endswith(tuple(rules.get("file_names_not_ends_with", ())))
        or (include and not any(re.search(rule, value) for rule in include for value in locations))
        or any(re.search(rule, value) for rule in rules.get("exclude", ()) for value in locations)
    ):
        return False
    content_extensions = rules.get("file_contains_regex_extensions", ())
    if (content := rules.get("file_contains_regex")) and (not content_extensions or extension in content_extensions):
        try:
            matched = bool(re.search("|".join(content), (source / path).read_text(errors="ignore"), re.MULTILINE))
        except OSError:
            # Let MegaLinter handle files the host could not read.
            matched = True
        return matched
    return True


def pr_linters(args, merge_base, lock, keys):
    source, files = args.source, args.diff
    # A consumer-supplied config can change descriptor filters or switch a linter to project mode.
    if (source / "stock.mega-linter.yml").is_file():
        return keys
    metadata = json.loads(LOCK.with_name("file-selectors.json").read_text())
    selectors = metadata["selectors"]
    if metadata["version"] != lock["version"] or selectors.keys() != lock["images"].keys():
        message = "Regenerate stock file selectors for the locked MegaLinter release"
        raise ValueError(message)
    return [
        key
        for key in keys
        if selectors[key] is None
        or any(
            selected_file(source, name, selectors[key])
            for name in (args.diff if key == "ACTION_ZIZMOR" else args.changed_files)
        )
    ]


def select_linter_keys(lock, requested, base):
    if requested:
        unknown = sorted(set(requested).difference(lock))
        if unknown:
            raise ValueError(f"Unsupported stock linter selection: {', '.join(unknown)}")
        return list(requested)
    return [key for key in lock if not (base and key == "REPOSITORY_SEMGREP")]


def scan_linter(key, digest, args, image_task=None):
    if key != "REPOSITORY_SEMGREP" or not args.base:
        return scan_one(key, digest, args, args.source, image_task)
    # Semgrep can reset its checkout during the baseline scan. A local clone
    # hard-links Git objects but gives it private refs, index and working files.
    with tempfile.TemporaryDirectory(prefix="stock-semgrep-", dir=args.source.parent) as directory:
        source = Path(directory)
        head = command("git", "rev-parse", "HEAD", cwd=args.source).stdout.strip()
        command("git", "clone", "--quiet", "--local", "--no-checkout", "--", str(args.source), str(source))
        command("git", "checkout", "--quiet", "--detach", head, cwd=source)
        command("git", "update-ref", "refs/remotes/origin/stock-scan-base", args.base, cwd=source)
        return scan_one(key, digest, args, source, image_task)


def scan(args):
    start = args.started = time.monotonic()
    source = args.source = args.source.resolve()
    reports = args.reports = args.reports.resolve()
    cache = args.cache = args.cache.resolve()
    reports.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    image_lock = image_pins()
    lock = image_lock["images"]
    keys = select_linter_keys(lock, args.linter, args.base)
    skipped = []
    base = args.base
    if base:
        if not re.fullmatch("[0-9a-f]{40}", base):
            message = "Base must be a full commit SHA"
            raise ValueError(message)
        merge_base = command("git", "merge-base", base, "HEAD", cwd=source).stdout.strip()
        command("git", "update-ref", "refs/remotes/origin/stock-scan-base", base, cwd=source)
        LOGGER.info("Scanning changes against %s", base)
        diff = command("git", "diff", "--no-renames", "--name-only", "-z", merge_base, "HEAD", cwd=source)
        args.diff = diff.stdout.rstrip("\0").split("\0") if diff.stdout else []
        args.changed_files = [
            name for name in args.diff if (source / name).is_file() and not (source / name).is_symlink()
        ]
        selected = pr_linters(args, merge_base, image_lock, keys)
        skipped = [key for key in keys if key not in selected]
        # The repository scans dominate the PR's critical path. Start both
        # before the shorter file checks fill the executor.
        keys = sorted(selected, key=lambda key: key != "REPOSITORY_SEMGREP")
        LOGGER.info("Selected %d linters; skipped %d without changed inputs", len(keys), len(skipped))
    cpus = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 1)
    docker_info = docker("info", "--format", "{{.NCPU}}\n{{json .SecurityOptions}}")
    daemon_cpus, security_options = docker_info.stdout.splitlines()
    cpus = min(cpus, int(daemon_cpus))
    args.rootless = "name=rootless" in (json.loads(security_options) or [])
    LOGGER.info("Docker daemon: %s (%d parallel container slots)", "rootless" if args.rootless else "rootful", cpus)
    with (cache / ".lock").open("a") as lease:
        fcntl.flock(lease, fcntl.LOCK_EX)
        remove_stale(lock, cache)
        with concurrent.futures.ThreadPoolExecutor(max_workers=cpus) as executor:
            tasks = []
            semgrep_image = None
            if args.semgrep_config and "REPOSITORY_SEMGREP" in keys:
                semgrep_image = executor.submit(image_for, "REPOSITORY_SEMGREP", lock["REPOSITORY_SEMGREP"])
                tasks.append(executor.submit(scan_semgrep_rules, semgrep_image, args))
            for key in keys:
                image_task = semgrep_image if key == "REPOSITORY_SEMGREP" else None
                tasks.append(executor.submit(scan_linter, key, lock[key], args, image_task))
            results = [task.result() for task in tasks]
        sizes = sum(path.stat().st_blocks * 512 for path in cache.rglob("*") if path.is_file())
    metrics = {
        "seconds": round(time.monotonic() - start, 2),
        "linters": results,
        "skipped_linters": skipped,
        "cache_disk_bytes": sizes,
        "image_logical_bytes": sum({row["image_id"]: row["image_bytes"] for row in results}.values()),
        "registry_layer_bytes": sum(row["registry_layer_bytes"] for row in results)
        if all(row["registry_layer_bytes"] is not None for row in results)
        else None,
        "actions_cache_bytes": 0 if args.persistent else None,
    }
    LOGGER.info("STOCK_CONTAINERS %s", json.dumps(metrics))
    (reports / "containers.json").write_text(json.dumps(metrics, indent=2) + "\n")
    summary(results, reports)
    return int(any(item["exit"] for item in results))


def benchmark_current(args):
    ref = args.benchmark_image
    if not re.fullmatch(r"ghcr\.io/[a-z0-9_.-]+/[a-z0-9_.-]+@sha256:[0-9a-f]{64}", ref):
        message = "The comparison image must be a digest-pinned GHCR reference"
        raise ValueError(message)
    registry_bytes, pull_seconds = pull(ref)
    image = require_image(ref)
    start = time.monotonic()
    workspace = "/github/workspace"
    options = mount(args.source.resolve(), workspace, writable=True)
    options += ["-e", f"DEFAULT_WORKSPACE={workspace}", "-e", f"GITHUB_WORKSPACE={workspace}"]
    for name in (
        "DEFAULT_BRANCH",
        "VALIDATE_ALL_CODEBASE",
        "APPLY_FIXES",
        "SEMGREP_ENABLE_VERSION_CHECK",
        "REPOSITORY_SEMGREP_ARGUMENTS",
        "REPOSITORY_SEMGREP_TIMEOUT_SECONDS",
    ):
        if name in os.environ:
            options += ["-e", name]
    result = docker("run", "--pull=never", "--rm", "--workdir", workspace, *options, ref, check=False)
    LOGGER.info("%s", result.stdout.rstrip())
    LOGGER.info(
        "STOCK_CONTAINERS %s",
        json.dumps(
            {
                "seconds": round(time.monotonic() - start, 2),
                "registry_layer_bytes": registry_bytes,
                "pull_seconds": pull_seconds,
                "image_logical_bytes": image["Size"],
                "cache_disk_bytes": 0,
                "actions_cache_bytes": 0,
            }
        ),
    )
    return result.returncode


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--reports", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--base", default="")
    parser.add_argument("--consumer-config", type=Path, help="Match an existing repository MegaLinter policy via uv")
    parser.add_argument("--semgrep-config", type=Path, help="Repository-relative Semgrep rules")
    parser.add_argument("--semgrep-pr-scope", choices=("auto", "full"), default="auto")
    parser.add_argument("--semgrep-targets", default="", help="Newline-separated Git pathspecs for explicit targets")
    parser.add_argument("--persistent", action="store_true")
    parser.add_argument("--advisory", action="store_true")
    parser.add_argument("--linter", action="append", help="Run only this key, for smoke checks")
    parser.add_argument("--benchmark-image", help="Measure a GHCR image with the legacy scanner entry point")
    args = parser.parse_args()
    args.consumer = None
    if args.consumer_config:
        args.consumer = consumer_policy(args.source.resolve(), args.consumer_config)
    if args.benchmark_image:
        sys.exit(benchmark_current(args))
    if args.reports is None or args.cache is None:
        parser.error("--reports and --cache are required for a per-linter scan")
    args.semgrep_targets = [path.strip() for path in args.semgrep_targets.splitlines() if path.strip()]
    if args.semgrep_targets and not args.semgrep_config:
        parser.error("--semgrep-targets requires --semgrep-config")
    if args.semgrep_config:
        args.semgrep_config = checkout_file(args.source.resolve(), args.semgrep_config)
    sys.exit(scan(args))


if __name__ == "__main__":
    main()
