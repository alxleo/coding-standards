package repo_standards.observability

import rego.v1

import data.repo_standards.helpers

# All checks gated on is_service — libraries/scripts/CLIs don't need these.

warn contains msg if {
	input.observability.is_service
	not input.observability.has_health_route
	not helpers.acknowledged("health_endpoint")
	msg := concat("\n", [
		"No health endpoint found (/health, /healthz, /ready)",
		"  Services need health checks for load balancers, container orchestration,",
		"  and monitoring. Fix: add a GET /health route returning 200 with status",
	])
}

warn contains msg if {
	input.observability.is_service
	not input.observability.has_metrics
	not helpers.acknowledged("metrics")
	msg := "No Prometheus client found — /metrics endpoint enables monitoring dashboards"
}

warn contains msg if {
	input.observability.is_service
	not input.observability.has_error_tracking
	not helpers.acknowledged("error_tracking")
	msg := "No error tracking SDK found (Sentry, Datadog) — errors in production need alerting"
}

warn contains msg if {
	input.observability.is_service
	not input.observability.has_tracing
	not helpers.acknowledged("tracing")
	msg := concat("\n", [
		"No tracing/OpenTelemetry SDK found",
		"  Distributed tracing connects requests across services.",
		"  Python: opentelemetry-sdk. JS: @opentelemetry/sdk-node",
	])
}
