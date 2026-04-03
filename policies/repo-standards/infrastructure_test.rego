package repo_standards.infrastructure_test

import rego.v1

import data.repo_standards.infrastructure

test_warn_missing_conftest_with_compose if {
	result := infrastructure.warn with input as {"content": {"compose_files": 3, "dockerfile_files": 0}, "files": {"conftest_toml": false, "editorconfig": true, "ci_json": true, "renovate": true}, "ci": {"has_sha_pins": false}, "acknowledged": {}}
	any_contains(result, "conftest.toml")
}

test_no_warn_conftest_without_compose if {
	result := infrastructure.warn with input as {"content": {"compose_files": 0, "dockerfile_files": 0}, "files": {"conftest_toml": false, "editorconfig": true, "ci_json": true, "renovate": true}, "ci": {"has_sha_pins": false}, "acknowledged": {}}
	not any_contains(result, "conftest.toml")
}

test_warn_missing_editorconfig if {
	result := infrastructure.warn with input as {"content": {"compose_files": 0, "dockerfile_files": 0}, "files": {"conftest_toml": true, "editorconfig": false, "ci_json": true, "renovate": true}, "ci": {"has_sha_pins": false}, "acknowledged": {}}
	any_contains(result, ".editorconfig")
}

test_warn_missing_ci_json_with_dockerfile if {
	result := infrastructure.warn with input as {"content": {"compose_files": 0, "dockerfile_files": 1}, "files": {"conftest_toml": true, "editorconfig": true, "ci_json": false, "renovate": true}, "ci": {"has_sha_pins": false}, "acknowledged": {}}
	any_contains(result, ".ci.json")
}

test_no_warn_ci_json_without_dockerfile if {
	result := infrastructure.warn with input as {"content": {"compose_files": 0, "dockerfile_files": 0}, "files": {"conftest_toml": true, "editorconfig": true, "ci_json": false, "renovate": true}, "ci": {"has_sha_pins": false}, "acknowledged": {}}
	not any_contains(result, ".ci.json")
}

test_warn_missing_renovate_with_pins if {
	result := infrastructure.warn with input as {"content": {"compose_files": 0, "dockerfile_files": 0}, "files": {"conftest_toml": true, "editorconfig": true, "ci_json": true, "renovate": false}, "ci": {"has_sha_pins": true}, "acknowledged": {}}
	any_contains(result, "renovate")
}

test_no_warn_renovate_without_pins if {
	result := infrastructure.warn with input as {"content": {"compose_files": 0, "dockerfile_files": 0}, "files": {"conftest_toml": true, "editorconfig": true, "ci_json": true, "renovate": false}, "ci": {"has_sha_pins": false}, "acknowledged": {}}
	not any_contains(result, "renovate")
}

test_warn_missing_dockle_with_dockerfile if {
	result := infrastructure.warn with input as {"content": {"compose_files": 0, "dockerfile_files": 1}, "files": {"conftest_toml": true, "editorconfig": true, "ci_json": true, "renovate": true}, "ci": {"has_sha_pins": false, "has_scheduled_dockle": false}, "acknowledged": {}}
	any_contains(result, "dockle")
}

test_no_warn_dockle_without_dockerfile if {
	result := infrastructure.warn with input as {"content": {"compose_files": 0, "dockerfile_files": 0}, "files": {"conftest_toml": true, "editorconfig": true, "ci_json": true, "renovate": true}, "ci": {"has_sha_pins": false, "has_scheduled_dockle": false}, "acknowledged": {}}
	not any_contains(result, "dockle")
}

test_no_warn_dockle_when_present if {
	result := infrastructure.warn with input as {"content": {"compose_files": 0, "dockerfile_files": 1}, "files": {"conftest_toml": true, "editorconfig": true, "ci_json": true, "renovate": true}, "ci": {"has_sha_pins": false, "has_scheduled_dockle": true}, "acknowledged": {}}
	not any_contains(result, "dockle")
}

any_contains(set, substring) if {
	some msg in set
	contains(msg, substring)
}
