package repo_standards.security

import rego.v1

import data.repo_standards.helpers

warn contains msg if {
	input.directories.secrets
	not input.files.gitleaks
	not helpers.acknowledged("gitleaks")
	msg := concat("\n", [
		".gitleaks.toml not found",
		"  secrets/ directory present — gitleaks needs path allowlists.",
		"  Fix: create .gitleaks.toml with [allowlist] paths for secret dirs",
	])
}

warn contains msg if {
	input.directories.decrypted
	not input.files.trivy
	not helpers.acknowledged("trivy")
	msg := concat("\n", [
		"trivy.yaml not found",
		"  .decrypted/ directory present — trivy scans the full filesystem.",
		"  Fix: create trivy.yaml with scan.skip-dirs for decrypted paths",
	])
}

warn contains msg if {
	input.directories.secrets
	not input.files.sops
	not helpers.acknowledged("sops")
	msg := concat("\n", [
		".sops.yaml not found",
		"  secrets/ directory present but no SOPS encryption config.",
		"  Fix: create .sops.yaml with age/pgp key and path rules",
	])
}

warn contains msg if {
	input.directories.decrypted
	not input.files.gitignore_covers_decrypted
	not helpers.acknowledged("gitignore_decrypted")
	msg := concat("\n", [
		".gitignore does not cover .decrypted/",
		"  Decrypted secrets may be accidentally committed.",
		"  Fix: add .decrypted/ to .gitignore",
	])
}

warn contains msg if {
	input.directories.secrets
	not input.files.env_example
	not helpers.acknowledged("env_example")
	msg := concat("\n", [
		".env.example not found",
		"  secrets/ present but no template documenting required env vars.",
		"  Fix: create .env.example with placeholder values for all required vars",
	])
}
