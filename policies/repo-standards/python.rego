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

warn contains msg if {
	input.content.python_files_with_hyphens > 0
	not helpers.acknowledged("python_hyphens")
	msg := sprintf(concat("\n", [
		"%d Python file(s) have hyphens in their names",
		"  Hyphens prevent importing — Python modules must be snake_case.",
		"  Fix: rename foo-bar.py to foo_bar.py",
	]), [input.content.python_files_with_hyphens])
}

warn contains msg if {
	input.content.python_files > 20
	not input.dependencies.structured_logging_py
	not helpers.acknowledged("structured_logging")
	msg := concat("\n", [
		"No structured logging library (structlog, python-json-logger)",
		"  print() and basic logging produce unstructured output.",
		"  Structured logs are searchable, parseable, and essential for debugging.",
		"  Fix: add structlog to dependencies",
	])
}

warn contains msg if {
	input.content.python_files > 0
	not input.dependencies.pydantic
	not helpers.acknowledged("pydantic")
	msg := concat("\n", [
		"pydantic not in dependencies",
		"  Runtime validation at boundaries (API, config, env) catches shape mismatches",
		"  that types alone can't — data from disk/network/user must be validated.",
		"  Fix: add pydantic to [project.dependencies]",
	])
}

warn contains msg if {
	input.content.python_files > 20
	not input.dependencies.import_linter
	not helpers.acknowledged("import_linter")
	msg := concat("\n", [
		"import-linter not in dependencies",
		"  Enforces allowed import directions between layers (e.g. models can't import CLI).",
		"  Catches architecture violations that compile fine but create coupling.",
		"  Fix: add import-linter to dev deps, define contracts in pyproject.toml",
	])
}

warn contains msg if {
	input.dependencies.import_linter
	not input.dependencies.import_linter_configured
	not helpers.acknowledged("import_linter_configured")
	msg := concat("\n", [
		"import-linter installed but no contracts defined",
		"  [tool.importlinter] section missing from pyproject.toml.",
		"  Without contracts, import-linter does nothing.",
		"  Fix: add [tool.importlinter] with contract_* sections defining layer rules",
	])
}

warn contains msg if {
	input.directories.tests
	input.content.python_files > 0
	not input.dependencies.hypothesis
	not helpers.acknowledged("hypothesis")
	msg := concat("\n", [
		"hypothesis not in dependencies",
		"  Property-based testing finds edge cases that example-based tests miss.",
		"  Especially valuable for parsing, serialization, and data transformation.",
		"  Fix: add hypothesis to test dependencies",
	])
}
