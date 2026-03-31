# TFLint baseline — synced to all repos.
# Consumer repos override by placing .tflint.hcl in their root.

config {
  call_module_type = "local"
}

rule "terraform_naming_convention" {
  enabled = true
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}
