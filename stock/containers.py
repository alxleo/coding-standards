# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Run the pinned MegaLinter images on one checkout."""

import argparse
import concurrent.futures
import fcntl
import fnmatch
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
import tomllib
import urllib.parse
from pathlib import Path
from typing import NamedTuple

IMAGE_PREFIX = "coding-standards-stock-owned/"
REGISTRY = "ghcr.io"
LOCK = Path(__file__).with_name("images.json")
DAY = 24 * 60 * 60
REPORT = "summary.md"
ZIZMOR_NO_INPUTS = 3
SOURCE = "/tmp/lint"  # noqa: S108 - reserved image workspace, mounted by Docker
POLICY = "/tmp/policy"  # noqa: S108 - read-only mount next to workspace
LOGGER = logging.getLogger(__name__)
ARCH = {"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64"}.get(platform.machine())
CURRENT_KEYS = {
    "ACTION_ZIZMOR": "REPOSITORY_ZIZMOR",
    "REPOSITORY_BETTERLEAKS": "REPOSITORY_BETTERLEAKS_GIT",
    "REPOSITORY_TRIVY": "REPOSITORY_TRIVY_CUSTOM",
}


class ConsumerPolicy(NamedTuple):
    blocking: set[str]
    ruff: Path | None
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


def fetch(host, path, headers=None):
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
        if match and f"sha256:{match[2]}" not in lock.get(match[1].upper(), {}).values():
            result = docker("image", "rm", tag, check=False)
            LOGGER.info("%s", result.stdout.rstrip())
    for kind, key in (("semgrep", "REPOSITORY_SEMGREP"), ("trivy", "REPOSITORY_TRIVY")):
        current = {digest.removeprefix("sha256:") for digest in lock[key].values()}
        for entry in cache.glob(f"{kind}-*"):
            suffix = entry.name.removeprefix(f"{kind}-")
            if (
                re.fullmatch("[0-9a-f]{64}", suffix)
                and suffix not in current
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


def fresh(path):
    return path.is_file() and time.time() - path.stat().st_mtime < DAY


def trivy_environment(directory):
    environment = {"TRIVY_CACHE_DIR": "/stock-data", "TRIVY_SKIP_VERSION_CHECK": "true"}
    for location, option in (
        ("db/metadata.json", "DB"),
        ("java-db/metadata.json", "JAVA_DB"),
        ("policy/metadata.json", "CHECK"),
    ):
        if fresh(directory / location):
            environment[f"TRIVY_SKIP_{option}_UPDATE"] = "true"
    return environment


def mount(path, target, *, writable=False):
    return ["--mount", f"type=bind,src={path},dst={target}" + ("" if writable else ",readonly")]


def trivy_setup(args, digest):
    directory = args.cache / f"trivy-{digest.removeprefix('sha256:')}"
    if not directory.exists():
        directory.mkdir()
        (directory / ".stock-owned").touch()
    env = trivy_environment(directory)
    if args.trivy_config:
        env.update(
            REPOSITORY_TRIVY_RULES_PATH=f"{SOURCE}/{args.trivy_config.parent}",
            REPOSITORY_TRIVY_CONFIG_FILE=args.trivy_config.name,
        )
    return mount(directory, "/stock-data", writable=True), env


def checkout_file(source, selection):
    path = source / selection
    if selection.is_absolute() or not path.resolve().is_relative_to(source) or not path.is_file():
        message = f"Expected a file inside the checkout: {selection}"
        raise ValueError(message)
    return path.resolve().relative_to(source)


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
    ruff = None
    if "PYTHON_RUFF" in enabled and (directory := policy.get("LINTER_RULES_PATH")):
        ruff = checkout_file(source, Path(directory) / policy.get("PYTHON_RUFF_CONFIG_FILE", "ruff.toml"))
    return ConsumerPolicy(enabled - advisory, ruff, ["--metrics=off", *semgrep])


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
        # The baseline reset can recreate directories in the local clone.
        # Keep them owned by the runner so it can remove the clone afterward.
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


def scan_semgrep_rules(digest, args):
    """Run the configured local rules with Semgrep's full-tree CLI."""
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

    ref, image, registry_bytes, pull_seconds = image_for("REPOSITORY_SEMGREP", digest)
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
        "--",
        ".",
        *(f"./{path}" for path in targets),
    ]
    start = time.monotonic()
    proc = run_scanner(options, command_line)
    elapsed = round(time.monotonic() - start, 2)
    (reports / "console.log").write_text(proc.stdout)
    findings = json.loads(report.read_text()) if report.is_file() else {}
    missing = set(targets).difference(findings.get("paths", {}).get("scanned", []))
    if missing:
        LOGGER.error("%s did not scan %d explicit targets: %s", key, len(missing), sorted(missing)[:20])
    errors = findings.get("errors", [])
    status = proc.returncode
    if status == 0 and (not findings or errors or missing):
        status = 1
    LOGGER.info(
        "%s scanned %d/%d explicit targets and reported %d findings",
        key,
        len(targets) - len(missing),
        len(targets),
        len(findings.get("results", [])),
    )
    if status:
        LOGGER.info("%s:\n%s", key, proc.stdout[-12000:])
    return {
        "linter": key,
        "seconds": elapsed,
        "scanner_seconds": elapsed,
        "exit": status,
        "pull_seconds": pull_seconds,
        "registry_layer_bytes": registry_bytes,
        "image_id": image["Id"],
        "image_bytes": image["Size"],
    }


def scan_one(key, digest, args, source):
    reports, base, advisory = args.reports, args.base, args.advisory
    if args.consumer:
        blocking = args.consumer.blocking
        advisory = advisory or (key not in blocking and CURRENT_KEYS.get(key) not in blocking)
    policy = LOCK.parent.parent.resolve()
    image_ref, image, registry_bytes, pull_seconds = image_for(key, digest)
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
        if args.consumer and (ruff := args.consumer.ruff):
            env.update(PYTHON_RUFF_RULES_PATH=f"{SOURCE}/{ruff.parent}", PYTHON_RUFF_CONFIG_FILE=ruff.name)
    if key == "REPOSITORY_TRIVY":
        data_mount, trivy_env = trivy_setup(args, digest)
        options += data_mount
        env.update(trivy_env)
    if key == "REPOSITORY_SEMGREP":
        data_mount, semgrep_env = semgrep_setup(args, digest, source, policy)
        options += data_mount
        env.update(semgrep_env)
    args = [image_ref]
    if key == "REPOSITORY_BETTERLEAKS" and base:
        # The pinned adapter adds a caret to the base and scans one extra commit.
        env.update(
            REPOSITORY_BETTERLEAKS_PR_COMMITS_SCAN="false",
            REPOSITORY_BETTERLEAKS_COMMAND_REMOVE_ARGUMENTS="dir",
            REPOSITORY_BETTERLEAKS_ARGUMENTS=f'git "--log-opts=--no-merges {base}..HEAD"',
        )
    if key == "ACTION_ZIZMOR":
        options += ["--entrypoint", "zizmor", "--network", "none"]
        args += [
            "--offline",
            "--collect",
            "workflows,actions",
            "--strict-collection",
            "--no-exit-codes" if advisory else "--format=plain",
            "--config",
            f"{POLICY}/lint-configs/.zizmor.yml",
            ".",
        ]
    for name, value in env.items():
        options += ["--env", f"{name}={value}"]

    start = time.monotonic()
    proc = run_scanner(options, args)
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


def python_dependency_sections(contents):
    project = tomllib.loads(contents)
    tools = project.get("tool", {})
    return (
        project.get("project"),
        project.get("build-system"),
        project.get("dependency-groups"),
        tools.get("poetry"),
        tools.get("uv"),
        tools.get("pdm"),
    )


def python_dependencies_changed(source, merge_base, name):
    manifest = source / name
    if manifest.is_symlink() or not manifest.is_file():
        return True
    previous = command("git", "show", f"{merge_base}:{name}", cwd=source, check=False)
    if previous.returncode:
        return True
    try:
        return python_dependency_sections(previous.stdout) != python_dependency_sections(manifest.read_text())
    except (OSError, tomllib.TOMLDecodeError, UnicodeError):
        return True


def trivy_pr_input(source, merge_base, files, lock, trivy_config):
    metadata = json.loads(LOCK.with_name("trivy-selectors.json").read_text())
    if metadata["images"] != lock["images"]["REPOSITORY_TRIVY"]:
        message = "Regenerate the Trivy PR selectors for the locked image"
        raise ValueError(message)
    docker_names = set(metadata["docker"])
    for name in files:
        path = Path(name)
        docker_parts = (path.name.lower().removeprefix("."), path.stem.lower(), path.suffix[1:].lower())
        if path == trivy_config or docker_names.intersection(docker_parts):
            return name
        if path.name == "pyproject.toml" and not python_dependencies_changed(source, merge_base, name):
            continue
        if any(fnmatch.fnmatchcase(path.name, pattern) for pattern in metadata["files"]):
            return name
    return None


def pr_linters(source, merge_base, lock, keys, trivy_config):
    diff = command("git", "diff", "--no-renames", "--name-only", "-z", merge_base, "HEAD", cwd=source)
    files = diff.stdout.split("\0")
    files = [name for name in files if name]
    if "REPOSITORY_TRIVY" in keys:
        if name := trivy_pr_input(source, merge_base, files, lock, trivy_config):
            LOGGER.info("Trivy PR selected by %r", name)
        else:
            LOGGER.info("Trivy PR skipped: no changed dependency, container or infrastructure inputs")
            keys = [key for key in keys if key != "REPOSITORY_TRIVY"]
    # A consumer-supplied config can change descriptor filters or switch a linter to project mode.
    if (source / "stock.mega-linter.yml").is_file():
        return keys
    metadata = json.loads(LOCK.with_name("file-selectors.json").read_text())
    selectors = metadata["selectors"]
    if metadata["version"] != lock["version"] or selectors.keys() != lock["images"].keys():
        message = "Regenerate stock file selectors for the locked MegaLinter release"
        raise ValueError(message)
    files = [name for name in files if (source / name).is_file() and not (source / name).is_symlink()]
    return [
        key
        for key in keys
        if selectors[key] is None or any(selected_file(source, name, selectors[key]) for name in files)
    ]


def scan_shared(key, digest, args):
    if key != "REPOSITORY_SEMGREP" or not args.base:
        return scan_one(key, digest, args, args.source)
    # Semgrep can reset its checkout during the baseline scan. A local clone
    # hard-links Git objects but gives it private refs, index and working files.
    with tempfile.TemporaryDirectory(prefix="stock-semgrep-", dir=args.source.parent) as directory:
        source = Path(directory)
        head = command("git", "rev-parse", "HEAD", cwd=args.source).stdout.strip()
        command("git", "clone", "--quiet", "--local", "--no-checkout", "--", str(args.source), str(source))
        command("git", "checkout", "--quiet", "--detach", head, cwd=source)
        command("git", "update-ref", "refs/remotes/origin/stock-scan-base", args.base, cwd=source)
        return scan_one(key, digest, args, source)


def scan_linter(key, digest, args):
    results = [scan_shared(key, digest, args)]
    if key == "REPOSITORY_SEMGREP" and args.semgrep_config:
        results.append(scan_semgrep_rules(digest, args))
    return results


def scan(args):
    start = time.monotonic()
    source = args.source = args.source.resolve()
    reports = args.reports = args.reports.resolve()
    cache = args.cache = args.cache.resolve()
    reports.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    image_lock = json.loads(LOCK.read_text())
    lock = image_lock["images"]
    keys = args.linter or list(lock)
    skipped = []
    base = args.base
    if base:
        if not re.fullmatch("[0-9a-f]{40}", base):
            message = "Base must be a full commit SHA"
            raise ValueError(message)
        merge_base = command("git", "merge-base", base, "HEAD", cwd=source).stdout.strip()
        command("git", "update-ref", "refs/remotes/origin/stock-scan-base", base, cwd=source)
        LOGGER.info("Scanning changes against %s", base)
        selected = pr_linters(source, merge_base, image_lock, keys, args.trivy_config)
        skipped = [key for key in keys if key not in selected]
        # The repository scans dominate the PR's critical path. Start both
        # before the shorter file checks fill the executor.
        keys = sorted(selected, key=lambda key: key not in ("REPOSITORY_SEMGREP", "REPOSITORY_TRIVY"))
        LOGGER.info("Selected %d linters; skipped %d without changed inputs", len(keys), len(skipped))
    cpus = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 1)
    cpus = min(cpus, int(docker("info", "--format", "{{.NCPU}}").stdout))
    with (cache / ".lock").open("a") as lease:
        fcntl.flock(lease, fcntl.LOCK_EX)
        remove_stale(lock, cache)
        with concurrent.futures.ThreadPoolExecutor(max_workers=cpus) as executor:
            tasks = [executor.submit(scan_linter, key, lock[key][ARCH], args) for key in keys]
            results = [result for task in tasks for result in task.result()]
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
        "TRIVY_CACHE_DIR",
        "SEMGREP_ENABLE_VERSION_CHECK",
        "REPOSITORY_SEMGREP_ARGUMENTS",
        "REPOSITORY_SEMGREP_TIMEOUT_SECONDS",
        "REPOSITORY_TRIVY_CUSTOM_CONFIG_FILE",
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
                "embedded_trivy_db": True,
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
    parser.add_argument("--trivy-config", type=Path, help="Repository-relative Trivy configuration")
    parser.add_argument("--consumer-config", type=Path, help="Match an existing repository MegaLinter policy via uv")
    parser.add_argument("--semgrep-config", type=Path, help="Repository-relative Semgrep rules for a full-tree scan")
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
    if args.trivy_config:
        source = args.source.resolve()
        config = (source / args.trivy_config).resolve()
        if args.trivy_config.is_absolute() or not config.is_relative_to(source) or not config.is_file():
            parser.error("--trivy-config must select a file inside the source checkout")
        args.trivy_config = config.relative_to(source)
    sys.exit(scan(args))


if __name__ == "__main__":
    main()
