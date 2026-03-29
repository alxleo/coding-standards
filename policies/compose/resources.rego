package compose.resources

import rego.v1

deny contains msg if {
	some svc_name, svc in input.services
	not svc.container_name
	msg := sprintf("service '%s' missing container_name", [svc_name])
}

deny contains msg if {
	some svc_name, svc in input.services
	not has_memory_limit(svc)
	msg := sprintf("service '%s' missing memory limit (deploy.resources.limits.memory or mem_limit)", [svc_name])
}

has_memory_limit(svc) if svc.mem_limit

has_memory_limit(svc) if svc.deploy.resources.limits.memory
