package repo_standards.quality

import rego.v1

import data.repo_standards.helpers

warn contains msg if {
	not input.directories.github_workflows
	not input.directories.gitea_workflows
	not helpers.acknowledged("ci_workflows")
	msg := "No CI workflow directory found (.github/workflows/ or .gitea/workflows/)"
}

warn contains msg if {
	not input.files.pre_commit_config
	not helpers.acknowledged("pre_commit")
	msg := concat("\n", [
		".pre-commit-config.yaml not found",
		"  Local hooks catch secrets and bad commits before they reach CI.",
		"  At minimum: detect-private-key + gitleaks + commitlint",
	])
}

warn contains msg if {
	not input.files.commitlint_config
	not helpers.acknowledged("commitlint_config")
	msg := "No commitlint config found — conventional commits make history readable"
}
