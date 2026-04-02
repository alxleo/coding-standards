package repo_standards.guide

import rego.v1

import data.repo_standards.helpers

# Always emit a single info-level message linking to the consumer guide.
# This ensures any LLM or human encountering repo-standards output can
# find the full documentation without prior knowledge.
warn contains msg if {
	not helpers.acknowledged("guide")
	msg := concat("\n", [
		"coding-standards repo-standards checks active",
		sprintf("  Docs: %s#repo-standards-setup-validation", [helpers.docs_url]),
		"  Catalog: https://github.com/alxleo/coding-standards/blob/main/docs/catalog.md",
		"  Acknowledge warnings: create .repo-standards.yml (see docs)",
	])
}
