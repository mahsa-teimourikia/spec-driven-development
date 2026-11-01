package northstar.approval

import rego.v1

# This policy is an illustrative OPA representation. The executable lab uses the
# versioned JSON policy so that the standard-library-only conformance suite is
# deterministic. Production adopters should select one authoritative evaluator.

default allow := false

required_roles := {"release_authority", "ai_governance_owner"} if {
  input.subject.action == "deploy"
  input.subject.environment == "production"
  input.subject.risk_tier == "CONSEQUENTIAL"
}

allow if {
  input.subject.policy_revision == "APPROVAL-POLICY@4"
  input.receipt_roles == required_roles
  count(input.receipt_principals) == count(required_roles)
  input.subject_digest == input.request_subject_digest
  input.receipts_current == true
  input.receipts_unused == true
}
