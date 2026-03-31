package repo_standards.infrastructure

import rego.v1

warn contains msg if {
	input.content.compose_files > 0
	not input.files.conftest_toml
	msg := concat("\n", [
		"conftest.toml not found",
		"  Docker Compose files present but compose policies won't run without it.",
		"  Policies check: healthchecks, resource limits, image pinning.",
		"  Fix: create conftest.toml with [policy.compose] dir = \"policy/compose\"",
	])
}

warn contains msg if {
	not input.files.editorconfig
	msg := ".editorconfig not found — ensures consistent formatting across editors"
}
