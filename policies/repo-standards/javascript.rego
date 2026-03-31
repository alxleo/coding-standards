package repo_standards.javascript

import rego.v1

warn contains msg if {
	input.content.typescript_files > 0
	not input.files.tsconfig
	msg := "tsconfig.json not found — TypeScript needs config for type checking"
}

warn contains msg if {
	(input.content.typescript_files + input.content.javascript_files) > 0
	not input.files.eslint_config
	msg := "No ESLint config found — linting config needed for JS/TS code"
}

warn contains msg if {
	input.directories.tests
	(input.content.typescript_files + input.content.javascript_files) > 0
	not input.dependencies.eslint_plugin_jest
	msg := concat("\n", [
		"eslint-plugin-jest not in dependencies",
		"  Catches tests with zero assertions (most common LLM test defect).",
		"  Fix: npm install -D eslint-plugin-jest and add to eslint config",
	])
}
