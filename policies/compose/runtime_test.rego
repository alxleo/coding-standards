package compose.runtime_test

import rego.v1

import data.compose.runtime

test_warn_unnamed_volume if {
	result := runtime.warn with input as {"services": {"app": {"volumes": ["/data"]}}}
	count(result) > 0
}

test_no_warn_named_volume if {
	result := runtime.warn with input as {"services": {"app": {"volumes": ["mydata:/data"], "restart": "unless-stopped", "logging": {"driver": "json-file"}}}}
	count(result) == 0
}

test_warn_host_networking if {
	result := runtime.warn with input as {"services": {"app": {"network_mode": "host", "restart": "always"}}}
	any_contains(result, "host networking")
}

test_warn_no_restart if {
	result := runtime.warn with input as {"services": {"app": {}}}
	any_contains(result, "restart policy")
}

test_no_warn_restart_present if {
	result := runtime.warn with input as {"services": {"app": {"restart": "unless-stopped"}}}
	not any_contains(result, "restart policy")
}

test_deny_privileged if {
	result := runtime.deny with input as {"services": {"app": {"privileged": true}}}
	any_contains(result, "privileged")
}

test_warn_bind_mount if {
	result := runtime.warn with input as {"services": {"app": {"volumes": ["/host/path:/container"], "restart": "always"}}}
	any_contains(result, "bind mount")
}

test_no_warn_docker_socket if {
	result := runtime.warn with input as {"services": {"app": {"volumes": ["/var/run/docker.sock:/var/run/docker.sock"], "restart": "always"}}}
	not any_contains(result, "bind mount")
}

test_warn_missing_logging if {
	result := runtime.warn with input as {"services": {"app": {"restart": "always"}}}
	any_contains(result, "logging")
}

test_no_warn_logging_present if {
	result := runtime.warn with input as {"services": {"app": {"restart": "always", "logging": {"driver": "json-file", "options": {"max-size": "10m"}}}}}
	not any_contains(result, "logging")
}

any_contains(set, substring) if {
	some msg in set
	contains(msg, substring)
}
