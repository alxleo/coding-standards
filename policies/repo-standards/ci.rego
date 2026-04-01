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
# ── Gitea CI patterns ─────────────────────────────────────────

warn contains msg if {
	helpers.has_ci_workflows
	not input.ci.run_blocks_have_groups
	not helpers.acknowledged("run_block_groups")
	msg := concat("\n", [
		"Workflow run: blocks missing ::group:: log markers",
		"  Gitea Actions and gitea-ci parse ::group::/::endgroup:: markers",
		"  for per-step log visibility. Without them, all step output merges",
		"  into one blob, making failure diagnosis difficult.",
		"  Fix: wrap multi-line run: blocks in echo \"::group::Step Name\" / echo \"::endgroup::\"",
		"  Use trap to ensure endgroup emits on failure: trap 'echo \"::endgroup::\"' EXIT",
	])
}

warn contains msg if {
	helpers.has_ci_workflows
	not input.ci.push_trigger_all_branches
	not helpers.acknowledged("push_trigger_branches")
	msg := concat("\n", [
		"Workflow push trigger filters by branch",
		"  The CI-on-every-commit model (Gitea) needs on: push: without branch",
		"  restrictions. A branches: [main] filter means feature branches get",
		"  no CI until they reach main — defeating the pre-push gate.",
		"  Fix: use on: push: (all branches) instead of on: push: branches: [main]",
	])
}

warn contains msg if {
	helpers.has_ci_workflows
	not input.ci.github_token_workaround
	not helpers.acknowledged("github_token_workaround")
	msg := concat("\n", [
		"Workflow uses github.com actions but lacks GITHUB_TOKEN workaround",
		"  Gitea overrides GITHUB_TOKEN with a Gitea-scoped token that can't",
		"  reach github.com APIs. Actions like setup-just (GitHub Releases) fail.",
		"  Fix: add early step: echo \"GITHUB_TOKEN=$REAL_GITHUB_TOKEN\" >> \"$GITHUB_ENV\"",
		"  and pass token explicitly: github-token: ${{ env.GITHUB_TOKEN }}",
	])
}
