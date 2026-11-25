# ruff: noqa: ERA001, INP001
import builtins as python_builtins
from builtins import isinstance as matches_type


def classify(value: object) -> tuple[bool, bool, bool]:
    # ruleid: coding-standards.catalog-no-isinstance
    bare = isinstance(value, str)
    # ruleid: coding-standards.catalog-no-isinstance
    qualified = python_builtins.isinstance(value, str)
    # ruleid: coding-standards.catalog-no-isinstance
    imported = matches_type(value, str)
    return bare, qualified, imported


def use_typed_value(value: str) -> str:
    # ok: coding-standards.catalog-no-isinstance
    return value.strip()
