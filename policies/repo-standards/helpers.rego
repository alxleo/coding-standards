package repo_standards.helpers

import rego.v1

# Check if a specific standard has been acknowledged by the consumer.
# Acknowledged checks are listed in .repo-standards.yml with a reason.
acknowledged(check_id) if {
	input.acknowledged[check_id]
}

# True when the repo has workflow files in either GitHub or Gitea location.
has_ci_workflows if {
	input.directories.github_workflows
}

has_ci_workflows if {
	input.directories.gitea_workflows
}
