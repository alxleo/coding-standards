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

test_warn_large_justfile_recipes if {
	result := quality.warn with input as {"content": {"justfile_recipes_over_10_lines": 2}}
	any_contains(result, "justfile recipe")
}

test_no_warn_small_justfile_recipes if {
	result := quality.warn with input as {"content": {"justfile_recipes_over_10_lines": 0}}
	not any_contains(result, "justfile recipe")
}

any_contains(set, substring) if {
	some msg in set
	contains(msg, substring)
}

test_warn_high_blast_radius if {
	result := quality.warn with input as {"content": {"max_blast_radius": 20, "max_naming_entropy": 0.5}}
	any_contains(result, "blast radius")
}

test_no_warn_low_blast_radius if {
	result := quality.warn with input as {"content": {"max_blast_radius": 5, "max_naming_entropy": 0.5}}
	not any_contains(result, "blast radius")
}

test_warn_high_entropy if {
	result := quality.warn with input as {"content": {"max_blast_radius": 3, "max_naming_entropy": 2.0}}
	any_contains(result, "naming entropy")
}

test_no_warn_low_entropy if {
	result := quality.warn with input as {"content": {"max_blast_radius": 3, "max_naming_entropy": 1.0}}
	not any_contains(result, "naming entropy")
}
