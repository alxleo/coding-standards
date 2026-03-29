package compose.images

import rego.v1

# Own images (ghcr.io/alxleo/*) must use :latest tag
deny contains msg if {
	some svc_name, svc in input.services
	image := svc.image
	startswith(image, "ghcr.io/alxleo/")
	not endswith(image, ":latest")
	msg := sprintf("service '%s' uses own image '%s' without :latest tag", [svc_name, image])
}
