# Validates config file consistency between .mega-linter-default.yml and lint-configs/.
package image_integrity.config_coverage

import rego.v1

# All config filenames referenced by _CONFIG_FILE entries
referenced_configs := {filename |
	some _, filename in input.config_files
}

# Config filenames referenced via _ARGUMENTS (e.g. --config=.mega-linter-config/.shellcheckrc)
argument_referenced_configs := {basename |
	some _, args in input.config_arguments
	some arg in args
	contains(arg, ".mega-linter-config/")
	basename := substring(arg, indexof(arg, ".mega-linter-config/") + count(".mega-linter-config/"), -1)
}

# Files that are exempt from reference checks
exempt_files := {
	".pre-commit-config.yaml", # pre-commit config, not a linter config
	".editorconfig", # copied to workspace root via PRE_COMMANDS (EditorConfig spec)
}

# Invariant 3: every _CONFIG_FILE value has a matching file in lint-configs/
deny contains msg if {
	some key, filename in input.config_files
	not filename in {f | some f in input.lint_config_files}
	msg := sprintf("%s: '%s' not found in lint-configs/", [key, filename])
}

# Invariant 4: every file in lint-configs/ is referenced somewhere
warn contains msg if {
	some file in input.lint_config_files
	not file in exempt_files
	not file in referenced_configs
	not file in argument_referenced_configs
	msg := sprintf("lint-configs/%s is unreferenced — not in any _CONFIG_FILE or _ARGUMENTS entry", [file])
}
