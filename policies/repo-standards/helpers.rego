package repo_standards.helpers

import rego.v1

# Consumer guide URL — included in warning messages for LLM/human discoverability
docs_url := "https://github.com/alxleo/coding-standards/blob/main/docs/consumer-guide.md"

# Check if a specific standard has been acknowledged by the consumer.
#
# Two formats in .repo-standards.yml:
#   repo-wide:  acknowledged: { check_id: "reason string" }
#   per-file:   acknowledged: { check_id: [{path: "...", reason: "..."}] }
#
# For repo-wide (string value): this helper returns true → policy skips entirely.
# For per-file (list value): the manifest generator already excluded those files
# from counts, so the policy sees reduced numbers. The raw list is preserved in
# the manifest for auditability.
acknowledged(check_id) if {
	value := input.acknowledged[check_id]
	is_string(value)
}

# True when the repo has workflow files in either GitHub or Gitea location.
has_ci_workflows if {
	input.directories.github_workflows
}

has_ci_workflows if {
	input.directories.gitea_workflows
}
