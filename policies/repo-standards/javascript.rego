package repo_standards.javascript

import rego.v1

import data.repo_standards.helpers

warn contains msg if {
	input.content.typescript_files > 0
	not input.files.tsconfig
	not helpers.acknowledged("tsconfig")
	msg := "tsconfig.json not found — TypeScript needs config for type checking"
}

warn contains msg if {
	(input.content.typescript_files + input.content.javascript_files) > 0
	not input.files.eslint_config
	not helpers.acknowledged("eslint_config")
	msg := "No ESLint config found — linting config needed for JS/TS code"
}

warn contains msg if {
	input.directories.tests
	(input.content.typescript_files + input.content.javascript_files) > 0
	not input.dependencies.eslint_plugin_jest
	not helpers.acknowledged("eslint_plugin_jest")
	msg := concat("\n", [
		"eslint-plugin-jest not in dependencies",
		"  Catches tests with zero assertions (most common LLM test defect).",
		"  Fix: npm install -D eslint-plugin-jest and add to eslint config",
	])
}

warn contains msg if {
	(input.content.typescript_files + input.content.javascript_files) > 0
	not input.files.nvmrc
	not helpers.acknowledged("nvmrc")
	msg := ".nvmrc not found — pin Node version for consistent builds across machines"
}

warn contains msg if {
	(input.content.typescript_files + input.content.javascript_files) > 0
	not input.dependencies.i18n_framework
	not helpers.acknowledged("i18n")
	msg := concat("\n", [
		"No i18n framework detected (i18next, react-intl, next-intl)",
		"  Hardcoded strings in JSX are painful to retrofit for translations.",
		"  Fix: npm install i18next react-i18next",
	])
}

warn contains msg if {
	(input.content.typescript_files + input.content.javascript_files) > 0
	not input.dependencies.structured_logging_js
	not helpers.acknowledged("structured_logging")
	msg := concat("\n", [
		"No structured logging library (pino, winston, bunyan)",
		"  console.log in production is unstructured and unsearchable.",
		"  Fix: npm install pino (fastest) or winston (most configurable)",
	])
}

warn contains msg if {
	(input.content.typescript_files + input.content.javascript_files) > 0
	not input.dependencies.zod
	not helpers.acknowledged("zod")
	msg := concat("\n", [
		"zod not in dependencies",
		"  Runtime validation at boundaries (API responses, config, user input).",
		"  Types check shape at compile time; Zod checks shape at runtime.",
		"  Fix: npm install zod",
	])
}

warn contains msg if {
	input.directories.tests
	(input.content.typescript_files + input.content.javascript_files) > 0
	not input.dependencies.stryker
	not helpers.acknowledged("stryker")
	msg := concat("\n", [
		"@stryker-mutator/core not in dependencies",
		"  Mutation testing verifies tests catch real bugs, not just execute.",
		"  Incremental mode mutates only changed code — fast enough for PR CI.",
		"  Setup: npx stryker init (generates stryker.config.mjs)",
		"  CI template: templates/stryker-mutation.yml in coding-standards repo",
	])
}
