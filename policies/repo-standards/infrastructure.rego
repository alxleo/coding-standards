package repo_standards.infrastructure

import rego.v1

import data.repo_standards.helpers

warn contains msg if {
	input.content.compose_files > 0
	not input.files.conftest_toml
	not helpers.acknowledged("conftest")
	msg := concat("\n", [
		"conftest.toml not found",
		"  Docker Compose files present but compose policies won't run without it.",
		"  Policies check: healthchecks, resource limits, image pinning.",
		"  Fix: create conftest.toml with [policy.compose] dir = \"policy/compose\"",
	])
}

warn contains msg if {
	not input.files.editorconfig
	not helpers.acknowledged("editorconfig")
	msg := ".editorconfig not found — ensures consistent formatting across editors"
}

warn contains msg if {
	input.content.dockerfile_files > 0
	not input.files.ci_json
	not helpers.acknowledged("ci_json")
	msg := concat("\n", [
		".ci.json not found",
		"  Dockerfile present but no data-driven smoke tests.",
		"  Without it, broken tool installs ship silently.",
		"  Fix: create .ci.json with {\"test_commands\": [\"tool --version\", ...]}",
	])
}

warn contains msg if {
	input.content.dockerfile_files > 0
	not input.ci.has_dockle
	not helpers.acknowledged("dockle")
	msg := concat("\n", [
		"No dockle image scan in CI workflows",
		"  Dockerfile present but no CIS Docker benchmark scanning.",
		"  Dockle catches: setuid binaries, empty passwords, duplicate UIDs.",
		"  Fix: add dockle to a scheduled workflow (scans built images, not Dockerfiles).",
	])
}

warn contains msg if {
	input.ci.has_sha_pins
	not input.files.renovate
	not helpers.acknowledged("renovate")
	msg := concat("\n", [
		"renovate.json not found",
		"  SHA-pinned actions or Docker images detected but no automated updates.",
		"  Without Renovate, pins go stale and miss security patches.",
		"  Fix: create renovate.json with extends: [\"config:recommended\"]",
	])
}
