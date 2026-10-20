package northstar.sdd.dispatch

default allow := false

required_gate_names := {
	"registry_integrity",
	"context_resolution",
	"authority_compatibility",
	"instruction_adapter_conformance",
	"execution_authorization",
	"delegation_attenuation",
	"audit_handoff_integrity",
}

allow if {
	input.control_plane_attestation_verified
	input.context_status == "VALIDATED"
	input.authorization_status == "VALID"
	input.gates == required_gate_names
	count(input.blocking_findings) == 0
}

deny_reasons contains "CONTROL_PLANE_ATTESTATION_INVALID" if {
	not input.control_plane_attestation_verified
}

deny_reasons contains "CONTEXT_NOT_VALIDATED" if {
	input.context_status != "VALIDATED"
}

deny_reasons contains "AUTHORIZATION_INVALID" if {
	input.authorization_status != "VALID"
}
