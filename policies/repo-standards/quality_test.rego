package repo_standards.quality_test

import rego.v1

import data.repo_standards.quality

test_warn_no_ci_workflows if {
	result := quality.warn with input as {"directories": {"github_workflows": false, "gitea_workflows": false}, "files": {"pre_commit_config": true, "commitlint_config": true}}
	any_contains(result, "CI workflow")
}

test_no_warn_github_workflows if {
	result := quality.warn with input as {"directories": {"github_workflows": true, "gitea_workflows": false}, "files": {"pre_commit_config": true, "commitlint_config": true}}
	not any_contains(result, "CI workflow")
}

test_no_warn_gitea_workflows if {
	result := quality.warn with input as {"directories": {"github_workflows": false, "gitea_workflows": true}, "files": {"pre_commit_config": true, "commitlint_config": true}}
	not any_contains(result, "CI workflow")
}

test_warn_no_pre_commit if {
	result := quality.warn with input as {"directories": {"github_workflows": true, "gitea_workflows": false}, "files": {"pre_commit_config": false, "commitlint_config": true}}
	any_contains(result, "pre-commit")
}

test_warn_pre_commit_missing_gitleaks if {
	result := quality.warn with input as {"files": {"pre_commit_config": true}, "content": {"pre_commit_hooks": ["detect-private-key", "commitlint"]}}
	any_contains(result, "gitleaks")
}

test_no_warn_pre_commit_has_gitleaks if {
	result := quality.warn with input as {"files": {"pre_commit_config": true}, "content": {"pre_commit_hooks": ["gitleaks", "detect-private-key"]}}
	not any_contains(result, "gitleaks")
}

test_warn_pre_commit_missing_detect_private_key if {
	result := quality.warn with input as {"files": {"pre_commit_config": true}, "content": {"pre_commit_hooks": ["gitleaks", "commitlint"]}}
	any_contains(result, "detect-private-key")
}

test_no_warn_pre_commit_has_detect_private_key if {
	result := quality.warn with input as {"files": {"pre_commit_config": true}, "content": {"pre_commit_hooks": ["gitleaks", "detect-private-key"]}}
	not any_contains(result, "detect-private-key")
}

any_contains(set, substring) if {
	some msg in set
	contains(msg, substring)
}
