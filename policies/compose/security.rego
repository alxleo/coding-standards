package compose.security

import rego.v1

# Docker socket mount gives full host control
deny contains msg if {
	some svc_name, svc in input.services
	some vol in svc.volumes
	is_string(vol)
	contains(vol, "docker.sock")
	not svc.read_only
	msg := sprintf("service '%s' mounts Docker socket — gives full host control. Use read-only (:ro) at minimum", [svc_name])
}

# no_new_privileges should be set for defense in depth
warn contains msg if {
	some svc_name, svc in input.services
	not _has_no_new_privileges(svc)
	msg := sprintf("service '%s' missing security_opt: no-new-privileges:true", [svc_name])
}

_has_no_new_privileges(svc) if {
	some opt in svc.security_opt
	opt == "no-new-privileges:true"
}

_has_no_new_privileges(svc) if {
	some opt in svc.security_opt
	opt == "no-new-privileges"
}

# Ports exposed to all interfaces (0.0.0.0) — should bind to 127.0.0.1 unless intentionally public
warn contains msg if {
	some svc_name, svc in input.services
	some port in svc.ports
	is_string(port)
	# "8080:8080" binds to 0.0.0.0 by default. "127.0.0.1:8080:8080" is explicit.
	regex.match(`^\d+:\d+$`, port)
	msg := sprintf("service '%s' exposes port %s to all interfaces — bind to 127.0.0.1 unless intentionally public", [svc_name, port])
}

# Sensitive host paths should never be mounted
deny contains msg if {
	some svc_name, svc in input.services
	some vol in svc.volumes
	is_string(vol)
	_is_sensitive_path(vol)
	msg := sprintf("service '%s' mounts sensitive host path '%s'", [svc_name, vol])
}

_is_sensitive_path(vol) if startswith(vol, "/etc:")
_is_sensitive_path(vol) if startswith(vol, "/proc:")
_is_sensitive_path(vol) if startswith(vol, "/sys:")
_is_sensitive_path(vol) if startswith(vol, "/dev:")

# Services should drop all capabilities and add back only what's needed
warn contains msg if {
	some svc_name, svc in input.services
	not _has_cap_drop_all(svc)
	msg := sprintf("service '%s' missing cap_drop: [ALL] — drop all capabilities and use cap_add for only what's needed", [svc_name])
}

_has_cap_drop_all(svc) if {
	some cap in svc.cap_drop
	cap == "ALL"
}

# Read-only root filesystem catches write-to-container bugs
warn contains msg if {
	some svc_name, svc in input.services
	not svc.read_only
	msg := sprintf("service '%s' missing read_only: true — read-only root filesystem prevents writes to container layer", [svc_name])
}
