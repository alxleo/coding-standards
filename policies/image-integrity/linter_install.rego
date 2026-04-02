# Validates that every enabled linter has an installed executable
# and that DISABLE_ERRORS entries are a subset of ENABLE_LINTERS.
package image_integrity.linter_install

import rego.v1

# All tools available in the image (pip + npm + binary)
all_installed_tools := {t | some t in input.dockerfile_tools.pip} |
	{t | some t in input.dockerfile_tools.npm} |
	{t | some t in input.dockerfile_tools.binary}

# Map of plugin linter names to their cli_executable
plugin_executables := {name: info.cli_executable |
	some name, info in input.plugins
}

# Tools that MegaLinter knows how to invoke (built-in descriptors).
# These still need binaries installed — this list maps linter IDs to
# the binary name MegaLinter will look for on PATH.
builtin_linter_executables := {
	"BASH_SHELLCHECK": "shellcheck",
	"BASH_SHFMT": "shfmt",
	"PYTHON_RUFF": "ruff",
	"PYTHON_PYRIGHT": "pyright",
	"YAML_YAMLLINT": "yamllint",
	"YAML_PRETTIER": "prettier",
	"YAML_V8R": "v8r",
	"JSON_PRETTIER": "prettier",
	"JSON_V8R": "v8r",
	"MARKDOWN_MARKDOWNLINT": "markdownlint",
	"DOCKERFILE_HADOLINT": "hadolint",
	"ACTION_ACTIONLINT": "actionlint",
	"TERRAFORM_TFLINT": "tflint",
	"EDITORCONFIG_EDITORCONFIG_CHECKER": "editorconfig-checker",
	"SPELL_CODESPELL": "codespell",
	"SPELL_LYCHEE": "lychee",
	"REPOSITORY_GITLEAKS": "gitleaks",
	"REPOSITORY_SEMGREP": "semgrep",
	"REPOSITORY_GIT_DIFF": "git",
	"JAVASCRIPT_ES": "eslint",
	"TYPESCRIPT_ES": "eslint",
	"JSX_ESLINT": "eslint",
	"TSX_ESLINT": "eslint",
	"JAVASCRIPT_PRETTIER": "prettier",
	"TYPESCRIPT_PRETTIER": "prettier",
	"CSS_STYLELINT": "stylelint",
	"ANSIBLE_ANSIBLE_LINT": "ansible-lint",
	"SQL_SQLFLUFF": "sqlfluff",
	"API_SPECTRAL": "spectral",
	"KUBERNETES_KUBECONFORM": "kubeconform",
	"MAKEFILE_CHECKMAKE": "checkmake",
	"GO_GOLANGCI_LINT": "golangci-lint",
	"HTML_HTMLHINT": "htmlhint",
	"REPOSITORY_LS_LINT": "ls-lint",
}

# Resolve a linter ID to the binary it needs
linter_executable(linter) := exe if {
	exe := builtin_linter_executables[linter]
} else := exe if {
	exe := plugin_executables[linter]
}

# npm/pip packages that install binaries under different names
install_aliases := {
	"attw": "@arethetypeswrong/cli",
	"depcruise": "dependency-cruiser",
	"lint-imports": "import-linter",
	"tsc": "typescript",
	"npm": "npm",
	"spectral": "@stoplight/spectral-cli",
	"ls-lint": "@ls-lint/ls-lint",
	"yamllint": "megalinter",
}

# Check if a binary name appears in any install list
binary_is_installed(exe) if exe in all_installed_tools

# Check via alias: binary "attw" → package "@arethetypeswrong/cli"
binary_is_installed(exe) if {
	pkg := install_aliases[exe]
	pkg in all_installed_tools
}

# Partial match: "ansible-lint" matches pip "ansible-lint"
binary_is_installed(exe) if {
	some tool in all_installed_tools
	contains(tool, exe)
}

binary_is_installed(exe) if {
	some tool in all_installed_tools
	contains(exe, tool)
}

# System packages (apk-installed, not in pip/npm/binary lists)
binary_is_installed("git")
binary_is_installed("npm")

# Invariant 1: every ENABLE_LINTERS entry has an executable
warn contains msg if {
	some linter in input.enable_linters
	exe := linter_executable(linter)
	not binary_is_installed(exe)
	msg := sprintf("ENABLE_LINTERS: %s needs '%s' but it's not installed in Dockerfile", [linter, exe])
}

# Linters with no known executable mapping (neither built-in nor plugin)
warn contains msg if {
	some linter in input.enable_linters
	not linter_executable(linter)
	not linter in object.keys(input.plugins)
	msg := sprintf("ENABLE_LINTERS: %s has no known executable mapping (not in builtins or plugins)", [linter])
}

# Invariant 2: every DISABLE_ERRORS entry is in ENABLE_LINTERS
deny contains msg if {
	some linter in input.disable_errors_linters
	not linter in {l | some l in input.enable_linters}
	msg := sprintf("DISABLE_ERRORS_LINTERS: %s is not in ENABLE_LINTERS (orphaned)", [linter])
}
