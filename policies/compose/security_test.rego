package compose.security_test

import rego.v1

import data.compose.security

test_deny_docker_socket_rw if {
	result := security.deny with input as {"services": {"app": {"volumes": ["/var/run/docker.sock:/var/run/docker.sock"]}}}
	count(result) > 0
}

test_warn_no_new_privileges_missing if {
	result := security.warn with input as {"services": {"app": {"ports": []}}}
	any_contains(result, "no-new-privileges")
}

test_no_warn_no_new_privileges_set if {
	result := security.warn with input as {"services": {"app": {"security_opt": ["no-new-privileges:true"], "ports": []}}}
	not any_contains(result, "no-new-privileges")
}

test_warn_port_all_interfaces if {
	result := security.warn with input as {"services": {"app": {"ports": ["8080:8080"], "security_opt": ["no-new-privileges:true"]}}}
	any_contains(result, "all interfaces")
}

test_no_warn_port_localhost if {
	result := security.warn with input as {"services": {"app": {"ports": ["127.0.0.1:8080:8080"], "security_opt": ["no-new-privileges:true"]}}}
	not any_contains(result, "all interfaces")
}

test_deny_sensitive_path if {
	result := security.deny with input as {"services": {"app": {"volumes": ["/etc:/host-etc"]}}}
	any_contains(result, "sensitive")
}

any_contains(set, substring) if {
	some msg in set
	contains(msg, substring)
}
