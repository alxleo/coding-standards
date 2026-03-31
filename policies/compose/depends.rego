package compose.depends

import rego.v1

# depends_on without service_healthy causes startup race conditions.
# Docker only waits for the container to START, not be READY.
warn contains msg if {
	some svc_name, svc in input.services
	some dep_name, dep_config in svc.depends_on
	is_object(dep_config)
	dep_config.condition == "service_started"
	msg := sprintf("service '%s' depends_on '%s' with condition: service_started — use service_healthy to wait for readiness", [svc_name, dep_name])
}

# depends_on as a bare list (no condition) defaults to service_started
warn contains msg if {
	some svc_name, svc in input.services
	is_array(svc.depends_on)
	some dep_name in svc.depends_on
	msg := sprintf("service '%s' depends_on '%s' without condition — defaults to service_started (race condition). Use condition: service_healthy", [svc_name, dep_name])
}
