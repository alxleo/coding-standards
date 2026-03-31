package compose.depends_test

import rego.v1

import data.compose.depends

test_warn_depends_on_service_started if {
	result := depends.warn with input as {"services": {"app": {"depends_on": {"db": {"condition": "service_started"}}}}}
	any_contains(result, "service_started")
}

test_no_warn_depends_on_service_healthy if {
	result := depends.warn with input as {"services": {"app": {"depends_on": {"db": {"condition": "service_healthy"}}}}}
	count(result) == 0
}

test_warn_depends_on_bare_list if {
	result := depends.warn with input as {"services": {"app": {"depends_on": ["db", "redis"]}}}
	count(result) == 2
}

any_contains(set, substring) if {
	some msg in set
	contains(msg, substring)
}
