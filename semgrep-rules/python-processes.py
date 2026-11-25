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
    subprocess.run(["python3", "-m", "megalinter.run"], check=False)
    # ok: coding-standards.python-helper-interpreter, coding-standards.python-subprocess-timeout
    subprocess.run(args=["python3", "-m", "megalinter.run", "--debug"], check=False)
    args = ["python3", "-m", "megalinter.run", "--debug"]
    # ok: coding-standards.python-helper-interpreter, coding-standards.python-subprocess-timeout
    subprocess.run(args, check=False)
    args = ["python3", "-m", "megalinter.run", "--debug"]
    # ok: coding-standards.python-helper-interpreter, coding-standards.python-subprocess-timeout
    subprocess.run(args=args, check=False)
    # ok: coding-standards.python-helper-interpreter, coding-standards.python-subprocess-timeout
    subprocess.Popen(["python3", "service.py"])


def display_labels() -> None:
    labels = ["python3", "helper.py"]
    # ok: coding-standards.python-helper-interpreter
    subprocess.run(["printf", "%s", str(labels)], check=True, timeout=5)
