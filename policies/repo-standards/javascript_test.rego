package repo_standards.javascript_test

import rego.v1

import data.repo_standards.javascript

test_warn_missing_tsconfig if {
	result := javascript.warn with input as {"content": {"typescript_files": 5, "javascript_files": 0}, "files": {"tsconfig": false, "eslint_config": true}, "directories": {"tests": false}, "dependencies": {}}
	any_contains(result, "tsconfig")
}

test_no_warn_tsconfig_no_ts if {
	result := javascript.warn with input as {"content": {"typescript_files": 0, "javascript_files": 3}, "files": {"tsconfig": false, "eslint_config": true}, "directories": {"tests": false}, "dependencies": {}}
	not any_contains(result, "tsconfig")
}

test_warn_missing_eslint if {
	result := javascript.warn with input as {"content": {"typescript_files": 0, "javascript_files": 5}, "files": {"tsconfig": false, "eslint_config": false}, "directories": {"tests": false}, "dependencies": {}}
	any_contains(result, "ESLint")
}

test_no_warn_when_no_js_ts if {
	result := javascript.warn with input as {"content": {"typescript_files": 0, "javascript_files": 0}, "files": {"tsconfig": false, "eslint_config": false}, "directories": {"tests": false}, "dependencies": {}}
	count(result) == 0
}

any_contains(set, substring) if {
	some msg in set
	contains(msg, substring)
}
