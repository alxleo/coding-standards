package repo_standards.security_test

import rego.v1

import data.repo_standards.security

test_warn_missing_gitleaks if {
	result := security.warn with input as {"directories": {"secrets": true, "decrypted": false}, "files": {"gitleaks": false, "sops": true}}
	any_contains(result, "gitleaks")
}

test_no_warn_gitleaks_no_secrets if {
	result := security.warn with input as {"directories": {"secrets": false, "decrypted": false}, "files": {"gitleaks": false, "sops": false, "gitignore_covers_decrypted": false}}
	count(result) == 0
}

test_warn_gitignore_missing_decrypted if {
	result := security.warn with input as {"directories": {"secrets": false, "decrypted": true}, "files": {"gitleaks": true, "gitignore_covers_decrypted": false}}
	any_contains(result, ".gitignore")
}

any_contains(set, substring) if {
	some msg in set
	contains(msg, substring)
}
