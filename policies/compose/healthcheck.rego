package compose.healthcheck

import rego.v1

deny contains msg if {
	some svc_name, svc in input.services
	not svc.healthcheck
	msg := sprintf("service '%s' missing healthcheck", [svc_name])
}

warn contains msg if {
	some svc_name, svc in input.services
	svc.healthcheck.disable == true
	msg := sprintf("service '%s' has healthcheck explicitly disabled", [svc_name])
}
