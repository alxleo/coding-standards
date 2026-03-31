package repo_standards.ci_test

import rego.v1

import data.repo_standards.ci

test_warn_missing_mega_linter if {
	result := ci.warn with input as {"files": {"mega_linter": false}, "directories": {"github_workflows": false}, "ci": {}}
	any_contains(result, "mega-linter.yml")
}

test_warn_no_extends if {
	result := ci.warn with input as {"files": {"mega_linter": true, "mega_linter_extends_url": null}, "directories": {"github_workflows": false}, "ci": {}}
	any_contains(result, "EXTENDS")
}

test_no_warn_extends_present if {
	result := ci.warn with input as {"files": {"mega_linter": true, "mega_linter_extends_url": "https://example.com"}, "directories": {"github_workflows": true}, "ci": {"workflow_uses_composite_action": true, "workflow_fetch_depth_zero": true, "workflow_persist_credentials_false": true, "workflow_actions_sha_pinned": true}}
	not any_contains(result, "EXTENDS")
	not any_contains(result, "mega-linter.yml not found")
}

test_warn_no_composite_action if {
	result := ci.warn with input as {"files": {"mega_linter": true, "mega_linter_extends_url": "https://example.com"}, "directories": {"github_workflows": true}, "ci": {"workflow_uses_composite_action": false, "workflow_fetch_depth_zero": true, "workflow_persist_credentials_false": true, "workflow_actions_sha_pinned": true}}
	any_contains(result, "docker-action")
}

test_warn_unpinned_actions if {
	result := ci.warn with input as {"files": {"mega_linter": true, "mega_linter_extends_url": "https://example.com"}, "directories": {"github_workflows": true}, "ci": {"workflow_uses_composite_action": true, "workflow_fetch_depth_zero": true, "workflow_persist_credentials_false": true, "workflow_actions_sha_pinned": false}}
	any_contains(result, "SHA-pinned")
}

any_contains(set, substring) if {
	some msg in set
	contains(msg, substring)
}
