package repo_standards.python_test

import rego.v1

import data.repo_standards.python

test_warn_missing_pyrightconfig if {
	result := python.warn with input as {"content": {"python_files": 10}, "files": {"pyrightconfig": false}, "directories": {"tests": false}, "dependencies": {}}
	count(result) > 0
}

test_no_warn_pyrightconfig_when_present if {
	result := python.warn with input as {"content": {"python_files": 10}, "files": {"pyrightconfig": true, "ruff": true}, "directories": {"tests": false}, "dependencies": {}}
	not any_contains(result, "pyrightconfig")
}

test_no_warn_when_no_python if {
	result := python.warn with input as {"content": {"python_files": 0}, "files": {"pyrightconfig": false, "ruff": false}, "directories": {"tests": false}, "dependencies": {}}
	count(result) == 0
}

test_warn_missing_ruff if {
	result := python.warn with input as {"content": {"python_files": 5}, "files": {"pyrightconfig": true, "ruff": false}, "directories": {"tests": false}, "dependencies": {}}
	any_contains(result, "ruff.toml")
}

test_warn_missing_pytest_randomly if {
	result := python.warn with input as {"content": {"python_files": 5}, "files": {"pyrightconfig": true, "ruff": true}, "directories": {"tests": true}, "dependencies": {"pytest_randomly": false, "test_deps_defined": true}}
	any_contains(result, "pytest-randomly")
}

test_no_warn_pytest_randomly_no_tests if {
	result := python.warn with input as {"content": {"python_files": 5}, "files": {"pyrightconfig": true, "ruff": true}, "directories": {"tests": false}, "dependencies": {"pytest_randomly": false}}
	not any_contains(result, "pytest-randomly")
}

test_acknowledged_silences_pyrightconfig if {
	result := python.warn with input as {
		"content": {"python_files": 10},
		"files": {"pyrightconfig": false, "ruff": true},
		"directories": {"tests": false},
		"dependencies": {},
		"acknowledged": {"pyrightconfig": "not needed — no local imports"},
	}
	not any_contains(result, "pyrightconfig")
}

test_acknowledged_silences_pytest_randomly if {
	result := python.warn with input as {
		"content": {"python_files": 5},
		"files": {"pyrightconfig": true, "ruff": true},
		"directories": {"tests": true},
		"dependencies": {"pytest_randomly": false, "test_deps_defined": true},
		"acknowledged": {"pytest_randomly": "tracked in #123"},
	}
	not any_contains(result, "pytest-randomly")
}

test_warn_missing_pydantic if {
	result := python.warn with input as {"content": {"python_files": 5}, "files": {"pyrightconfig": true, "ruff": true}, "directories": {"tests": false}, "dependencies": {"pydantic": false, "import_linter": false}, "acknowledged": {}}
	any_contains(result, "pydantic")
}

test_no_warn_pydantic_when_present if {
	result := python.warn with input as {"content": {"python_files": 5}, "files": {"pyrightconfig": true, "ruff": true}, "directories": {"tests": false}, "dependencies": {"pydantic": true, "import_linter": true}, "acknowledged": {}}
	not any_contains(result, "pydantic")
}

test_warn_missing_import_linter_large_project if {
	result := python.warn with input as {"content": {"python_files": 25}, "files": {"pyrightconfig": true, "ruff": true}, "directories": {"tests": false}, "dependencies": {"pydantic": true, "import_linter": false}, "acknowledged": {}}
	any_contains(result, "import-linter")
}

test_no_warn_import_linter_small_project if {
	result := python.warn with input as {"content": {"python_files": 10}, "files": {"pyrightconfig": true, "ruff": true}, "directories": {"tests": false}, "dependencies": {"pydantic": true, "import_linter": false}, "acknowledged": {}}
	not any_contains(result, "import-linter")
}

any_contains(set, substring) if {
	some msg in set
	contains(msg, substring)
}
