package northstar.architecture

import rego.v1

default allow := false

deny contains finding if {
  some imported in input.observation.imports
  imported.module in {"openai", "anthropic", "provider_sdk"}
  finding := {
    "rule_id": "EA-001",
    "code": "DIRECT_MODEL_PROVIDER_DEPENDENCY",
    "resource": imported.file,
    "message": "Use the enterprise AI gateway."
  }
}

deny contains finding if {
  some imported in input.observation.imports
  startswith(imported.module, "underwriting_database")
  finding := {
    "rule_id": "EA-004",
    "code": "PRIVATE_DATASTORE_ACCESS",
    "resource": imported.file,
    "message": "Use the governed underwriting data API."
  }
}

allow if {
  count(deny) == 0
  input.observation.policy_version == input.authority.active_policy_version
}
