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

test_warn_inline_linting if {
	result := ci.warn with input as {"files": {"mega_linter": true, "mega_linter_extends_url": "https://example.com"}, "directories": {"github_workflows": true}, "ci": {"workflow_uses_composite_action": true, "workflow_fetch_depth_zero": true, "workflow_persist_credentials_false": true, "workflow_actions_sha_pinned": true, "ci_delegates_to_runner": false}}
	any_contains(result, "inline linting")
}

test_no_warn_delegates_to_runner if {
	result := ci.warn with input as {"files": {"mega_linter": true, "mega_linter_extends_url": "https://example.com"}, "directories": {"github_workflows": true}, "ci": {"workflow_uses_composite_action": true, "workflow_fetch_depth_zero": true, "workflow_persist_credentials_false": true, "workflow_actions_sha_pinned": true, "ci_delegates_to_runner": true}}
	not any_contains(result, "inline linting")
}

test_warn_mixed_schedule_and_push if {
	result := ci.warn with input as {"files": {"mega_linter": true, "mega_linter_extends_url": "https://example.com"}, "directories": {"github_workflows": true}, "ci": {"workflow_uses_composite_action": true, "workflow_fetch_depth_zero": true, "workflow_persist_credentials_false": true, "workflow_actions_sha_pinned": true, "ci_delegates_to_runner": true, "ci_mixes_schedule_and_push": true}}
	any_contains(result, "schedule triggers")
}

test_no_warn_separated_schedules if {
	result := ci.warn with input as {"files": {"mega_linter": true, "mega_linter_extends_url": "https://example.com"}, "directories": {"github_workflows": true}, "ci": {"workflow_uses_composite_action": true, "workflow_fetch_depth_zero": true, "workflow_persist_credentials_false": true, "workflow_actions_sha_pinned": true, "ci_delegates_to_runner": true, "ci_mixes_schedule_and_push": false}}
	not any_contains(result, "schedule triggers")
}

# ── Gitea CI patterns ─────────────────────────────────────────

test_warn_missing_group_markers if {
	result := ci.warn with input as {"files": {"mega_linter": true, "mega_linter_extends_url": "https://example.com"}, "directories": {"github_workflows": true}, "ci": {"workflow_uses_composite_action": true, "workflow_fetch_depth_zero": true, "workflow_persist_credentials_false": true, "workflow_actions_sha_pinned": true, "ci_delegates_to_runner": true, "ci_mixes_schedule_and_push": false, "run_blocks_have_groups": false, "push_trigger_all_branches": true, "github_token_workaround": true}}
	any_contains(result, "::group::")
}

test_no_warn_group_markers_present if {
	result := ci.warn with input as {"files": {"mega_linter": true, "mega_linter_extends_url": "https://example.com"}, "directories": {"github_workflows": true}, "ci": {"workflow_uses_composite_action": true, "workflow_fetch_depth_zero": true, "workflow_persist_credentials_false": true, "workflow_actions_sha_pinned": true, "ci_delegates_to_runner": true, "ci_mixes_schedule_and_push": false, "run_blocks_have_groups": true, "push_trigger_all_branches": true, "github_token_workaround": true}}
	not any_contains(result, "::group::")
}

test_warn_push_branch_filter if {
	result := ci.warn with input as {"files": {"mega_linter": true, "mega_linter_extends_url": "https://example.com"}, "directories": {"github_workflows": true}, "ci": {"workflow_uses_composite_action": true, "workflow_fetch_depth_zero": true, "workflow_persist_credentials_false": true, "workflow_actions_sha_pinned": true, "ci_delegates_to_runner": true, "ci_mixes_schedule_and_push": false, "run_blocks_have_groups": true, "push_trigger_all_branches": false, "github_token_workaround": true}}
	any_contains(result, "push trigger filters")
}

test_no_warn_push_all_branches if {
	result := ci.warn with input as {"files": {"mega_linter": true, "mega_linter_extends_url": "https://example.com"}, "directories": {"github_workflows": true}, "ci": {"workflow_uses_composite_action": true, "workflow_fetch_depth_zero": true, "workflow_persist_credentials_false": true, "workflow_actions_sha_pinned": true, "ci_delegates_to_runner": true, "ci_mixes_schedule_and_push": false, "run_blocks_have_groups": true, "push_trigger_all_branches": true, "github_token_workaround": true}}
	not any_contains(result, "push trigger filters")
}

test_warn_missing_github_token_workaround if {
	result := ci.warn with input as {"files": {"mega_linter": true, "mega_linter_extends_url": "https://example.com"}, "directories": {"github_workflows": true}, "ci": {"workflow_uses_composite_action": true, "workflow_fetch_depth_zero": true, "workflow_persist_credentials_false": true, "workflow_actions_sha_pinned": true, "ci_delegates_to_runner": true, "ci_mixes_schedule_and_push": false, "run_blocks_have_groups": true, "push_trigger_all_branches": true, "github_token_workaround": false}}
	any_contains(result, "GITHUB_TOKEN workaround")
}

test_no_warn_github_token_workaround_present if {
	result := ci.warn with input as {"files": {"mega_linter": true, "mega_linter_extends_url": "https://example.com"}, "directories": {"github_workflows": true}, "ci": {"workflow_uses_composite_action": true, "workflow_fetch_depth_zero": true, "workflow_persist_credentials_false": true, "workflow_actions_sha_pinned": true, "ci_delegates_to_runner": true, "ci_mixes_schedule_and_push": false, "run_blocks_have_groups": true, "push_trigger_all_branches": true, "github_token_workaround": true}}
	not any_contains(result, "GITHUB_TOKEN workaround")
}

any_contains(set, substring) if {
	some msg in set
	contains(msg, substring)
}
