"""Baked semgrep exclusions must name rule IDs as semgrep reports them.

Semgrep prefixes every rule loaded from a local config with the config's
directory, and --exclude-rule matches the full ID exactly. The image loads
all rulesets from /rules, so an exclusion without the `rules.` prefix is
silently a no-op (verified with semgrep 1.182.1: a rule with id
`trailofbits.generic.x.x` read from /rules/trailofbits.json reports as
`rules.trailofbits.generic.x.x`).
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BAKED = yaml.safe_load((ROOT / ".mega-linter-default.yml").read_text())


def _excluded_rules() -> list[str]:
    args = BAKED.get("REPOSITORY_SEMGREP_ARGUMENTS", [])
    return [arg.split("=", 1)[1] for arg in args if arg.startswith("--exclude-rule=")]


def _custom_rule_ids() -> set[str]:
    ids = set()
    for path in (ROOT / "semgrep-rules").glob("*.yml"):
        if path.name.endswith(".test.yml"):
            continue
        for rule in (yaml.safe_load(path.read_text()) or {}).get("rules", []):
            ids.add(rule["id"])
    return ids


def test_baked_rulesets_all_load_from_rules_dir():
    rulesets = BAKED["REPOSITORY_SEMGREP_RULESETS"]
    assert rulesets, "expected baked semgrep rulesets"
    assert all(ruleset.startswith("/rules/") for ruleset in rulesets), rulesets


def test_exclusions_use_the_reported_rule_id():
    excluded = _excluded_rules()
    assert excluded, "expected baked --exclude-rule arguments"
    unprefixed = [rule for rule in excluded if not rule.startswith("rules.")]
    assert not unprefixed, f"--exclude-rule needs the full rules.* ID, these match nothing: {unprefixed}"


def test_custom_rule_exclusions_name_existing_rules():
    custom = _custom_rule_ids()
    for rule in _excluded_rules():
        if rule.startswith("rules.custom."):
            assert rule.removeprefix("rules.custom.") in custom, f"{rule} names no rule in semgrep-rules/"
