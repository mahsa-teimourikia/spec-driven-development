package northstar.ai_governance

import rego.v1

default allow := false

allow if {
  input.use_case.lifecycle == "APPROVED_FOR_BOUNDED_USE"
  input.model.status == "APPROVED"
  input.evaluation.status == "PASS"
  input.controls.human_oversight == "VERIFIED"
  input.controls.authoritative_mutation == "DENIED"
}

# Teaching excerpt only. The Python control plane authenticates inputs, resolves
# current registry state, consumes exact approval, and performs enforcement.
