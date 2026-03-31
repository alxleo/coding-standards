package repo_standards.python

import rego.v1

import data.repo_standards.helpers

warn contains msg if {
	input.content.python_files > 0
	not input.files.pyrightconfig
	not helpers.acknowledged("pyrightconfig")
	msg := concat("\n", [
		"pyrightconfig.json not found",
		"  Pyright needs extraPaths to resolve local imports. Without it,",
		"  missing-import warnings may block CI.",
		"  Fix: create pyrightconfig.json with {\"extraPaths\": [\"scripts\"]}",
	])
}

warn contains msg if {
	input.content.python_files > 0
	not input.files.ruff
	not helpers.acknowledged("ruff")
	msg := concat("\n", [
		"ruff.toml not found",
		"  Consumer override needed for per-file-ignores (test/, scripts/).",
		"  Without it, the baked baseline may produce false positives.",
		"  Fix: create ruff.toml extending the baseline rules",
	])
}

warn contains msg if {
	input.directories.tests
	input.content.python_files > 0
	not input.dependencies.pytest_randomly
	not helpers.acknowledged("pytest_randomly")
	msg := concat("\n", [
		"pytest-randomly not in dependencies",
		"  Catches hidden test order dependencies. Zero config, just install.",
		"  Fix: add pytest-randomly to [project.optional-dependencies] test group",
	])
}

warn contains msg if {
	input.directories.tests
	input.content.python_files > 0
	not input.dependencies.test_deps_defined
	not helpers.acknowledged("test_deps")
	msg := concat("\n", [
		"tests/ directory exists but no test framework in pyproject.toml",
		"  Fix: add pytest to [project.optional-dependencies] or [dependency-groups]",
	])
}
