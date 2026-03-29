package compose.resources_test

import rego.v1

import data.compose.resources

test_deny_missing_container_name if {
	result := resources.deny with input as {"services": {"web": {}}}
	count(result) > 0
}

test_deny_missing_memory_limit if {
	result := resources.deny with input as {"services": {"web": {"container_name": "web"}}}
	some msg in result
	contains(msg, "missing memory limit")
}

test_allow_mem_limit if {
	result := resources.deny with input as {"services": {"web": {
		"container_name": "web",
		"mem_limit": "512m",
	}}}
	count({msg | some msg in result; contains(msg, "memory")}) == 0
}

test_allow_deploy_resources if {
	result := resources.deny with input as {"services": {"web": {
		"container_name": "web",
		"deploy": {"resources": {"limits": {"memory": "512m"}}},
	}}}
	count({msg | some msg in result; contains(msg, "memory")}) == 0
}
