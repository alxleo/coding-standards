package compose.runtime

import rego.v1

# Unnamed volumes lose data on container recreation
warn contains msg if {
	some svc_name, svc in input.services
	some vol in svc.volumes
	is_string(vol)
	not contains(vol, ":")
	msg := sprintf("service '%s' has unnamed volume '%s' — use named volumes for persistence", [svc_name, vol])
}

# Host networking bypasses Docker network isolation
warn contains msg if {
	some svc_name, svc in input.services
	svc.network_mode == "host"
	msg := sprintf("service '%s' uses host networking — loses container isolation", [svc_name])
}

# Missing restart policy means service stays down after crash
warn contains msg if {
	some svc_name, svc in input.services
	not svc.restart
	not svc.deploy.restart_policy
	msg := sprintf("service '%s' has no restart policy — won't recover from crashes", [svc_name])
}

# Privileged mode gives full host access (already in semgrep, reinforced here)
deny contains msg if {
	some svc_name, svc in input.services
	svc.privileged == true
	msg := sprintf("service '%s' is privileged — use specific cap_add instead", [svc_name])
}

# Bind mounts from host are fragile — prefer named volumes
warn contains msg if {
	some svc_name, svc in input.services
	some vol in svc.volumes
	is_string(vol)
	startswith(vol, "/")
	not contains(vol, "/var/run/docker.sock")
	msg := sprintf("service '%s' uses host bind mount '%s' — consider named volumes for portability", [svc_name, vol])
}

# Missing logging config risks disk exhaustion from unrotated logs
warn contains msg if {
	some svc_name, svc in input.services
	not svc.logging
	msg := sprintf("service '%s' has no logging config — unrotated logs can exhaust disk. Set logging.driver and logging.options.max-size", [svc_name])
}
