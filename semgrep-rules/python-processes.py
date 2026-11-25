# ruff: noqa: ERA001, INP001, S603, S607
import subprocess
import sys
from subprocess import check_output as capture


def helper_argv() -> None:
    # ruleid: coding-standards.python-helper-interpreter
    subprocess.run(["python3", "helper.py"], check=True, timeout=5)
    # ruleid: coding-standards.python-helper-interpreter
    subprocess.run(args=["python", "helper.py"], check=True, timeout=5)
    # ruleid: coding-standards.python-helper-interpreter
    args = ["python3", "helper.py"]
    capture(args, timeout=5)
    # ok: coding-standards.python-helper-interpreter
    subprocess.run([sys.executable, "helper.py"], check=True, timeout=5)


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
    subprocess.Popen(["python3", "service.py"])


def display_labels() -> list[str]:
    # ok: coding-standards.python-helper-interpreter
    return ["python3", "helper.py"]
