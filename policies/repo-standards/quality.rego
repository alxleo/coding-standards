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

warn contains msg if {
	not input.files.envrc
	not helpers.acknowledged("envrc")
	msg := concat("\n", [
		".envrc not found",
		"  direnv auto-loads env vars on cd. Non-secret config (URLs, paths, IDs).",
		"  Secrets stay in shell profile / keychain, not .envrc.",
		"  Fix: create .envrc with project-specific env vars",
	])
}

warn contains msg if {
	input.suppressions.total > 20
	not helpers.acknowledged("suppression_count")
	msg := sprintf(concat("\n", [
		"%d suppression comments found across codebase",
		"  Each suppression is a TODO or a design question being avoided.",
		"  Run: docker run ... coding-standards:latest standards — see suppressions breakdown",
	]), [input.suppressions.total])
}

warn contains msg if {
	not input.files.makefile
	not helpers.acknowledged("makefile")
	msg := concat("\n", [
		"No Makefile or justfile found",
		"  Unified check command (make check / just check) ensures nothing is skipped.",
		"  If an LLM has to remember 4 commands, it'll skip some.",
		"  Fix: create justfile or Makefile with check/test/lint recipes",
	])
}

warn contains msg if {
	input.content.python_files > 5
	not input.directories.tests
	not helpers.acknowledged("no_tests")
	msg := concat("\n", [
		"No tests/ directory but Python scripts present",
		"  Scripts without tests are untestable assumptions.",
		"  Fix: create tests/ with pytest tests for your scripts",
	])
}

warn contains msg if {
	input.content.shell_scripts_over_50_lines > 0
	not helpers.acknowledged("large_shell_scripts")
	msg := sprintf(concat("\n", [
		"%d shell script(s) exceed 50 lines",
		"  Shell is for glue (wiring commands together). When scripts need loops",
		"  with conditionals, data parsing, or error handling, rewrite in Python.",
		"  Shell scripts are hard to test; Python scripts get pytest for free.",
	]), [input.content.shell_scripts_over_50_lines])
}
