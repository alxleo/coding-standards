package repo_standards.helpers

import rego.v1

# Consumer guide URL — included in warning messages for LLM/human discoverability
docs_url := "https://github.com/alxleo/coding-standards/blob/main/docs/consumer-guide.md"

# Check if a specific standard has been acknowledged by the consumer.
#
# Three formats in .repo-standards.yml:
#   permanent:  acknowledged: { check_id: "reason string" }
#   temporary:  acknowledged: { check_id: {reason: "...", expires: "YYYY-MM-DD"} }
#   per-file:   acknowledged: { check_id: [{path: "...", reason: "..."}] }
#
# Permanent (string) and temporary (object with reason) both suppress.
# Expired temporaries are stripped by the manifest generator before Rego sees them.
# Per-file (list) entries are resolved during manifest generation (excluded from counts).
acknowledged(check_id) if {
	value := input.acknowledged[check_id]
	is_string(value)
}

acknowledged(check_id) if {
	value := input.acknowledged[check_id]
	is_object(value)
	value.reason
}

# True when the repo has workflow files in either GitHub or Gitea location.
has_ci_workflows if {
	input.directories.github_workflows
}

has_ci_workflows if {
	input.directories.gitea_workflows
}
