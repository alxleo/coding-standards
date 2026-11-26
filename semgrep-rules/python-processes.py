# ruff: noqa: ERA001, INP001, S603, S607
import subprocess
import sys
from subprocess import check_output as capture


def helper_argv(directory: str) -> None:
    # ruleid: coding-standards.python-helper-interpreter
    subprocess.run(["python3", "helper.py"], check=True, timeout=5)
    # ruleid: coding-standards.python-helper-interpreter
    subprocess.run(args=["python", "helper.py"], check=True, timeout=5)
    args = ["python3.14", "helper.py"]
    # Another statement can separate construction from execution.
    timeout = 10
    # ruleid: coding-standards.python-helper-interpreter
    capture(args, cwd=directory, timeout=timeout)
    # ok: coding-standards.python-helper-interpreter
    subprocess.run([sys.executable, "helper.py"], check=True, timeout=5)
    # ok: coding-standards.python-helper-interpreter
    capture(["python3", "--version"], timeout=5)


def timeouts() -> None:
    # ruleid: coding-standards.python-subprocess-timeout
    subprocess.run(["git", "status"], check=True)
    # ruleid: coding-standards.python-subprocess-timeout
    capture(["git", "status"], timeout=None)
    # ok: coding-standards.python-subprocess-timeout
    capture(["git", "status"], timeout=5)
    # ok: coding-standards.python-helper-interpreter, coding-standards.python-subprocess-timeout
    subprocess.Popen(["python3", "service.py"])


def long_running_linter() -> None:
    args = ["python3", "-m", "megalinter.run", "--debug"]
    directory = "workspace"
    # ok: coding-standards.python-helper-interpreter, coding-standards.python-subprocess-timeout
    # nosemgrep: coding-standards.python-helper-interpreter, coding-standards.python-subprocess-timeout
    subprocess.run(args=args, cwd=directory, check=False)


def display_labels() -> None:
    labels = ["python3", "helper.py"]
    # ok: coding-standards.python-helper-interpreter
    subprocess.run(["printf", "%s", str(labels)], check=True, timeout=5)
