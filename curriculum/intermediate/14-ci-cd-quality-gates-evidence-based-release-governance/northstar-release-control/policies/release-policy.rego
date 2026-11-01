package northstar.release

import rego.v1

default allow := false

required_checks := {"sbom", "functional", "ai_evaluation", "security"}

allow if {
    input.environment == "production"
    every check in required_checks {
        input.verified_checks[check] == "PASS"
    }
    input.artifact_digest == input.approved_artifact_digest
    input.point_of_use_revalidation == "PASS"
    input.approval_policy_revision == input.current_policy_revision
    input.approval_authority_revision == input.current_authority_revision
    input.current_scoped_authority == "ACTIVE"
    input.release_approval_valid
    input.ai_governance_approval_valid
}

# Teaching policy only. The Python control plane resolves and authenticates inputs.
