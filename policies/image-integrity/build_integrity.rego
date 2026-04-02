# Validates Docker build integrity: COPY sources in CI hash, dual-arch checksums.
package image_integrity.build_integrity

import rego.v1

# Arch-agnostic tools (Java-based, etc.) don't need dual checksums
arch_agnostic_tools := {"pmd"}

# Invariant 5: every Dockerfile COPY source is covered by CI context hash.
# A COPY source is covered if the hash patterns include it directly or via a glob.
warn contains msg if {
	some source in input.dockerfile_copy_sources
	not source_in_hash(source)
	msg := sprintf("Dockerfile COPY '%s' not covered by CI hashFiles() — cache won't invalidate on change", [source])
}

# Check if a COPY source is covered by any hash pattern
source_in_hash(source) if {
	some pattern in input.ci_hash_patterns
	pattern == source
}

# Glob match: "plugins/**" covers "plugins/"
source_in_hash(source) if {
	some pattern in input.ci_hash_patterns
	endswith(pattern, "/**")
	prefix := substring(pattern, 0, count(pattern) - 3)
	startswith(source, prefix)
}

# Individual file in a directory covered by glob: "scripts/foo.py" covered by "scripts/ci/**"
source_in_hash(source) if {
	some pattern in input.ci_hash_patterns
	not contains(pattern, "*")
	# Direct prefix match for individual files
	dir := substring(source, 0, count(source) - count(basename(source)))
	pattern_dir := substring(pattern, 0, count(pattern) - count(basename(pattern)))
	dir == pattern_dir
}

basename(path) := part if {
	parts := split(path, "/")
	part := parts[count(parts) - 1]
}

# Invariant 6: every binary download has dual-arch checksums
# (except arch-agnostic tools like PMD which use JVM)
deny contains msg if {
	some tool, checksums in input.dockerfile_binary_checksums
	not tool in arch_agnostic_tools
	not checksums.amd64
	msg := sprintf("Binary '%s' missing amd64 SHA256", [tool])
}

deny contains msg if {
	some tool, checksums in input.dockerfile_binary_checksums
	not tool in arch_agnostic_tools
	not checksums.arm64
	msg := sprintf("Binary '%s' missing arm64 SHA256 — arm64 build will fail", [tool])
}

deny contains msg if {
	some tool, checksums in input.dockerfile_binary_checksums
	not tool in arch_agnostic_tools
	checksums.amd64
	checksums.arm64
	checksums.amd64 == checksums.arm64
	msg := sprintf("Binary '%s' has identical amd64/arm64 SHA256 — likely copy-paste error", [tool])
}
