package repo_standards.infrastructure_test

import rego.v1

import data.repo_standards.infrastructure

test_warn_missing_conftest_with_compose if {
	result := infrastructure.warn with input as {"content": {"compose_files": 3}, "files": {"conftest_toml": false, "editorconfig": true}}
	any_contains(result, "conftest.toml")
}

test_no_warn_conftest_without_compose if {
	result := infrastructure.warn with input as {"content": {"compose_files": 0}, "files": {"conftest_toml": false, "editorconfig": true}}
	not any_contains(result, "conftest.toml")
}

test_warn_missing_editorconfig if {
	result := infrastructure.warn with input as {"content": {"compose_files": 0}, "files": {"conftest_toml": true, "editorconfig": false}}
	any_contains(result, ".editorconfig")
}

any_contains(set, substring) if {
	some msg in set
	contains(msg, substring)
}
