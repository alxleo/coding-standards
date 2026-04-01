package repo_standards.ci

import rego.v1

import data.repo_standards.helpers

warn contains msg if {
	not input.files.mega_linter
	not helpers.acknowledged("mega_linter")
	msg := concat("\n", [
		".mega-linter.yml not found",
		"  Needed to inherit baseline config via EXTENDS URL.",
		"  Fix: create .mega-linter.yml with EXTENDS pointing at coding-standards baseline",
	])
}

warn contains msg if {
	input.files.mega_linter
	input.files.mega_linter_extends_url == null
	not helpers.acknowledged("extends_url")
	msg := concat("\n", [
		".mega-linter.yml exists but has no EXTENDS URL",
		"  Without EXTENDS, the repo doesn't inherit baseline linter config.",
		"  Fix: add EXTENDS: [https://raw.githubusercontent.com/alxleo/coding-standards/main/.mega-linter-default.yml]",
	])
}

warn contains msg if {
	helpers.has_ci_workflows
	not input.ci.workflow_uses_composite_action
	not helpers.acknowledged("composite_action")
	msg := concat("\n", [
		"No workflow references coding-standards/docker-action",
		"  The composite action is the standard way to run MegaLinter in CI.",
		"  Fix: add uses: alxleo/coding-standards/docker-action@<sha> # v1 — SHA-pin for supply chain safety",
	])
}

warn contains msg if {
	helpers.has_ci_workflows
	not input.ci.workflow_fetch_depth_zero
	not helpers.acknowledged("fetch_depth")
	msg := concat("\n", [
		"No workflow uses fetch-depth: 0",
		"  Gitleaks and commitlint need full git history.",
		"  Fix: add fetch-depth: 0 to your checkout step",
	])
}

warn contains msg if {
	helpers.has_ci_workflows
	not input.ci.workflow_persist_credentials_false
	not helpers.acknowledged("persist_credentials")
	msg := "persist-credentials: false not set in checkout — security best practice"
}

warn contains msg if {
	helpers.has_ci_workflows
	not input.ci.workflow_actions_sha_pinned
	not helpers.acknowledged("sha_pinned")
	msg := concat("\n", [
		"Not all GitHub Actions are SHA-pinned",
		"  Supply chain safety: pin actions to commit SHAs, not tags.",
		"  Zizmor will also flag this as unpinned-uses.",
	])
}

warn contains msg if {
	helpers.has_ci_workflows
	not input.ci.ci_delegates_to_runner
	not helpers.acknowledged("ci_delegates")
	msg := concat("\n", [
		"CI has inline linting commands instead of delegating to a task runner",
		"  Inline ruff/pytest/semgrep in CI drifts from local dev, causing",
		"  'passes locally, fails CI' pain. CI should call `just check` or",
		"  `make check` — one command that runs identically everywhere.",
		"  Fix: move linting commands into a justfile/Makefile recipe,",
		"  add that recipe to pre-commit, and have CI call the recipe.",
	])
}

warn contains msg if {
	helpers.has_ci_workflows
	input.ci.ci_mixes_schedule_and_push
	not helpers.acknowledged("ci_schedule_separation")
	msg := concat("\n", [
		"CI workflow mixes schedule triggers with push/PR triggers",
		"  Scheduled jobs (trivy, dependency updates) are operational.",
		"  PR/push jobs are CI. Mixing them adds conditional complexity",
		"  (if: github.event_name != 'schedule') that obscures the pipeline.",
		"  Fix: separate into ci.yml (PR + push) and scheduled.yml (cron).",
	])
}

warn contains msg if {
	helpers.has_ci_workflows
	input.ci.ci_run_blocks_over_10_lines > 0
	not helpers.acknowledged("large_ci_run_blocks")
	msg := sprintf(concat("\n", [
		"%d CI workflow run: block(s) exceed 10 lines",
		"  Orchestration files delegate — they don't implement.",
		"  Fix: extract long run: blocks into scripts/ and call by path.",
	]), [input.ci.ci_run_blocks_over_10_lines])
}
