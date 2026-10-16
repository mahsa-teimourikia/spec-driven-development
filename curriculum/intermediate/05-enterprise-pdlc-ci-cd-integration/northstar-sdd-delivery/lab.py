#!/usr/bin/env python3
"""Deterministic Course 15 lab: connect SDD artifacts to trusted delivery gates."""

from __future__ import annotations

import copy
import fnmatch
import hashlib
import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
STATUSES = {"PASS", "REVIEW", "BLOCK", "NOT_APPLICABLE"}
REQUIRED_GATES = (
    "specification_readiness",
    "implementation_conformance",
    "technical_quality",
    "evidence_integrity",
    "control_provenance",
    "integration_readiness",
    "integration_authorization",
    "deployment_authorization",
    "runtime_conformance",
)
_RECEIPT_LOCK = threading.Lock()


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    severity: str
    subject: str
    message: str


@dataclass(frozen=True)
class GateResult:
    gate: str
    status: str
    findings: tuple[Finding, ...]

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"unknown gate status: {self.status}")


def finding(code: str, subject: str, message: str, severity: str = "BLOCK") -> Finding:
    return Finding(code, severity, subject, message)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_control_plane() -> dict[str, Any]:
    return read_json(ROOT / "policy" / "trusted-control-plane.json")


def load_reference() -> dict[str, Any]:
    return read_json(ROOT / "reference" / "delivery-package.json")


def load_candidate() -> dict[str, Any]:
    package = load_reference()
    descriptor = read_json(ROOT / "candidate" / "delivery-package.json")
    for patch in descriptor["patches"]:
        apply_patch(package, patch)
    package["fixture_status"] = descriptor["fixture_status"]
    return package


def load_candidate_control() -> dict[str, Any]:
    control = load_control_plane()
    observations = read_json(ROOT / "candidate" / "trusted-observations.json")
    for patch in observations["control_patches"]:
        apply_patch(control, patch)
    return control


def canonical_system_digest(components: dict[str, Any]) -> str:
    payload = json.dumps(components, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def exact_transition_subject(package: dict[str, Any], *, deployment: bool = False) -> dict[str, Any]:
    components = package.get("effective_ai_system_revision", {}).get("components", {})
    subject = {
        "change_id": package["change_manifest"]["change_id"],
        "commit": package["pull_request"]["head_sha"],
        "specification_revision": package["change_manifest"]["specification_revision"],
        "system_revision": canonical_system_digest(components),
    }
    if deployment:
        subject.update({
            "artifact_digest": package.get("build", {}).get("artifact_digest"),
            "environment": package.get("deployment", {}).get("environment"),
        })
    return subject


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _at(root: dict[str, Any], path: str) -> tuple[Any, str]:
    parts = [part.replace("~1", "/").replace("~0", "~") for part in path.strip("/").split("/")]
    if not parts or parts == [""]:
        raise ValueError("patch path must identify a field")
    node: Any = root
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node, parts[-1]


def apply_patch(root: dict[str, Any], patch: dict[str, Any]) -> None:
    node, key = _at(root, patch["path"])
    operation = patch.get("op", "replace")
    if operation == "replace":
        if isinstance(node, list):
            node[int(key)] = copy.deepcopy(patch["value"])
        else:
            node[key] = copy.deepcopy(patch["value"])
    elif operation == "append":
        target = node[int(key)] if isinstance(node, list) else node[key]
        target.append(copy.deepcopy(patch["value"]))
    elif operation == "remove":
        if isinstance(node, list):
            node.pop(int(key))
        else:
            node.pop(key, None)
    else:
        raise ValueError(f"unsupported patch operation: {operation}")


def _gate(gate: str, findings: list[Finding], *, applicable: bool = True) -> GateResult:
    if not applicable:
        return GateResult(gate, "NOT_APPLICABLE", ())
    status = "BLOCK" if any(item.severity == "BLOCK" for item in findings) else "REVIEW" if findings else "PASS"
    return GateResult(gate, status, tuple(sorted(findings)))


def validate_specification(package: dict[str, Any], control: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    manifest = package.get("change_manifest", {})
    current = control["current"]
    if manifest.get("specification_revision") != current["specification_revision"]:
        results.append(finding("SPEC_REVISION_STALE", "change-manifest", "The PR is not bound to the current approved specification revision."))
    if manifest.get("context_digest") != current["context_digest"]:
        results.append(finding("CONTEXT_REVALIDATION_REQUIRED", "change-manifest", "The effective policy and architecture context changed after planning."))
    if manifest.get("base_revision") != current["base_revision"]:
        results.append(finding("BASE_REVISION_STALE", "change-manifest", "The implementation was planned from a stale repository revision."))
    if set(manifest.get("policy_revisions", [])) != set(current["policy_revisions"]):
        results.append(finding("POLICY_REVISION_STALE", "change-manifest", "The policy revision set must be re-resolved before delivery."))
    if manifest.get("risk_tier") not in control["risk_profiles"]:
        results.append(finding("RISK_PROFILE_UNKNOWN", "change-manifest", "No governed gate profile exists for this risk tier."))
    if manifest.get("open_decisions"):
        results.append(finding("OPEN_DECISION_UNRESOLVED", "change-manifest", "An accountable decision remains open.", "REVIEW"))
    system = package.get("effective_ai_system_revision", {})
    components = system.get("components", {})
    computed = canonical_system_digest(components) if isinstance(components, dict) else ""
    if computed != system.get("digest"):
        results.append(finding("SYSTEM_REVISION_DIGEST_INVALID", "effective-ai-system", "The declared system digest does not match its canonical component identities."))
    if components != control.get("component_registry"):
        results.append(finding("SYSTEM_COMPONENT_IDENTITY_UNVERIFIED", "effective-ai-system", "The package component identities do not match the trusted component registry."))
    return results


def validate_implementation(package: dict[str, Any], control: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    manifest = package.get("change_manifest", {})
    pull_request = package.get("pull_request", {})
    source = control.get("source_control", {})
    if not source.get("attestation_verified"):
        results.append(finding("SOURCE_CONTROL_ATTESTATION_INVALID", "source-control", "The authoritative base, head, and diff were not verified by the Git provider."))
    if pull_request.get("head_sha") != source.get("head_sha") or manifest.get("base_revision") != source.get("base_revision"):
        results.append(finding("SOURCE_REVISION_SUBJECT_MISMATCH", "pull-request", "The package is not bound to the trusted provider's exact base and head revisions."))
    changed_paths = set(source.get("changed_paths", []))
    declared_paths = set(pull_request.get("changed_paths", []))
    if declared_paths != changed_paths:
        results.append(finding("PR_DIFF_CLAIM_MISMATCH", "pull-request", "The package path summary differs from the authoritative Git-provider diff."))
    allowed = list(manifest.get("authorized_paths", []))
    protected = list(control["protected_paths"])
    outside_scope = {path for path in changed_paths if not any(fnmatch.fnmatchcase(path, pattern) for pattern in allowed)}
    protected_changes = {path for path in changed_paths if any(fnmatch.fnmatchcase(path, pattern) for pattern in protected)}
    if outside_scope or protected_changes:
        results.append(finding("AWU_SCOPE_VIOLATION", "pull-request", "The authoritative diff crosses the approved work-unit path boundary."))

    expected = control["protected_requirement_hashes"]
    observed = package.get("requirements", {}).get("semantic_hashes", {})
    for requirement_id, semantic_hash in expected.items():
        if observed.get(requirement_id) != semantic_hash:
            results.append(finding("UNAUTHORIZED_REQUIREMENT_CHANGE", requirement_id, "A protected requirement changed without owner authorization."))

    requirement_ids = set(package.get("requirements", {}).get("applicable_ids", []))
    links = package.get("traceability", [])
    covered = {item.get("requirement_id") for item in links if item.get("implementation") and item.get("evidence_claim_ids")}
    if requirement_ids - covered:
        results.append(finding("TRACEABILITY_GAP", "traceability", "Every applicable requirement needs implementation and evidence ancestry."))
    if any(item.get("change_id") != manifest.get("change_id") for item in links):
        results.append(finding("TRACEABILITY_SUBJECT_MISMATCH", "traceability", "A trace link belongs to another change."))
    return results


def validate_technical_quality(package: dict[str, Any], _control: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    technical = package.get("technical_results", {})
    if technical.get("unit_tests") != "PASS" or technical.get("static_analysis") != "PASS":
        results.append(finding("TECHNICAL_GATE_FAILED", "technical-results", "Required engineering checks did not pass."))
    if technical.get("producer") == package.get("pull_request", {}).get("author"):
        results.append(finding("SELF_REPORTED_TECHNICAL_RESULT", "technical-results", "Author-produced results are signals, not independent proof.", "REVIEW"))
    return results


def required_claims(package: dict[str, Any]) -> set[str]:
    return {
        claim
        for link in package.get("traceability", [])
        for claim in link.get("evidence_claim_ids", [])
    }


def validate_evidence(package: dict[str, Any], control: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    manifest = package.get("change_manifest", {})
    required = required_claims(package)
    valid: set[str] = set()
    trusted = set(control["trusted_evidence_producers"])
    registry = control.get("evidence_registry", {})
    assertion_fields = {"producer", "independent", "result", "subject", "expires_at", "attestation_verified"}
    for claim in package.get("evidence_manifest", {}).get("records", []):
        claim_id = claim.get("claim_id", "unknown")
        if assertion_fields & set(claim):
            results.append(finding("UNTRUSTED_EVIDENCE_ASSERTION", claim_id, "PR-controlled evidence metadata cannot establish producer, result, independence, or subject."))
        evidence_id = claim.get("evidence_id")
        record = registry.get(evidence_id)
        if not record:
            results.append(finding("EVIDENCE_RECORD_NOT_FOUND", str(evidence_id), "The referenced evidence ID was not found in the trusted verifier registry."))
            continue
        if record.get("claim_id") != claim_id:
            results.append(finding("EVIDENCE_CLAIM_MISMATCH", str(evidence_id), "The trusted evidence record supports a different claim."))
            continue
        if (
            record.get("producer") not in trusted
            or not record.get("producer_identity_verified")
            or not record.get("attestation_verified")
            or not record.get("independent")
        ):
            results.append(finding("UNTRUSTED_EVIDENCE_PRODUCER", claim_id, "The trusted registry did not authenticate an approved independent verifier and attestation."))
            continue
        expected_subject = {
            "change_id": manifest.get("change_id"),
            "commit": package.get("pull_request", {}).get("head_sha"),
            "specification_revision": manifest.get("specification_revision"),
            "system_revision": canonical_system_digest(package.get("effective_ai_system_revision", {}).get("components", {})),
        }
        if record.get("subject") != expected_subject:
            results.append(finding("EVIDENCE_SUBJECT_MISMATCH", claim_id, "Evidence is bound to a different change, commit, specification, or AI-system revision."))
            continue
        if record.get("result") != "PASS":
            results.append(finding("EVIDENCE_CLAIM_FAILED", claim_id, "The claim-specific verifier did not pass."))
            continue
        if record.get("expires_at") and _parse_time(record["expires_at"]) <= _parse_time(control["evaluation_time"]):
            results.append(finding("EVIDENCE_EXPIRED", claim_id, "The evidence expired before the decision time."))
            continue
        valid.add(claim_id)
    if required - valid:
        results.append(finding("REQUIRED_EVIDENCE_MISSING", "evidence-manifest", "At least one required claim lacks valid independent evidence."))
    return results


def validate_control_provenance(package: dict[str, Any], control: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    observed = package.get("control_provenance", {})
    expected = control["validator"]
    if observed != expected:
        results.append(finding("CONTROL_PROVENANCE_CLAIM_MISMATCH", "validator", "The package's validator claim differs from the trusted control-plane configuration."))
    execution = control.get("execution_attestation", {})
    if (
        not execution.get("attestation_verified")
        or not execution.get("protected_workflow")
        or execution.get("validator_repository") != expected.get("repository")
        or execution.get("validator_revision") != expected.get("revision")
    ):
        results.append(finding("CONTROL_PROVENANCE_INVALID", "validator", "Trusted execution did not authenticate the protected validator workload and revision."))
    authoritative_paths = control.get("source_control", {}).get("changed_paths", [])
    if any(path.startswith(".github/workflows/") or path.startswith("delivery-control/") for path in authoritative_paths):
        results.append(finding("CONTROL_PROVENANCE_INVALID", "pull-request", "The authoritative diff changes controls that judge the same PR."))
    return results


def validate_integration_readiness(package: dict[str, Any], control: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    queue = package.get("merge_queue", {})
    if queue.get("base_sha") != control["current"]["integration_base_sha"]:
        results.append(finding("MERGE_QUEUE_BASE_STALE", "merge-queue", "The queued candidate is not tested against the current integration base."))
    if queue.get("semantic_conflicts"):
        results.append(finding("SEMANTIC_MERGE_CONFLICT", "merge-queue", "Concurrent changes are textually mergeable but semantically incompatible."))
    if queue.get("revalidation_status") != "PASS":
        results.append(finding("MERGE_QUEUE_REVALIDATION_MISSING", "merge-queue", "The exact queued merge candidate has not passed required revalidation."))
    return results


def verify_receipt(
    package: dict[str, Any], control: dict[str, Any], receipt_id: str | None, *, kind: str
) -> list[Finding]:
    if not receipt_id:
        return [finding(f"INVALID_{kind}_AUTHORIZATION", kind.lower(), "The requested transition has no authorization receipt.")]
    receipt = control["receipts"].get(receipt_id)
    if not receipt or receipt.get("kind") != kind:
        return [finding(f"INVALID_{kind}_AUTHORIZATION", receipt_id, "The receipt is unknown or has the wrong authorization kind.")]
    results: list[Finding] = []
    if receipt.get("state") != "AVAILABLE":
        results.append(finding(f"INVALID_{kind}_AUTHORIZATION", receipt_id, "The receipt is revoked, consumed, or otherwise unavailable."))
    if _parse_time(receipt["expires_at"]) <= _parse_time(control["evaluation_time"]):
        results.append(finding(f"INVALID_{kind}_AUTHORIZATION", receipt_id, "The authorization receipt expired."))
    expected = exact_transition_subject(package, deployment=kind == "DEPLOYMENT")
    if receipt.get("subject") != expected:
        results.append(finding(f"INVALID_{kind}_AUTHORIZATION", receipt_id, "The receipt is not bound to the exact transition subject."))
    return results


def base_gate_results(package: dict[str, Any], control: dict[str, Any]) -> list[GateResult]:
    return [
        _gate("specification_readiness", validate_specification(package, control)),
        _gate("implementation_conformance", validate_implementation(package, control)),
        _gate("technical_quality", validate_technical_quality(package, control)),
        _gate("evidence_integrity", validate_evidence(package, control)),
        _gate("control_provenance", validate_control_provenance(package, control)),
        _gate("integration_readiness", validate_integration_readiness(package, control)),
    ]


def integration_completed(package: dict[str, Any], control: dict[str, Any]) -> bool:
    subject = exact_transition_subject(package)
    return subject in control.get("completed_integrations", [])


def validate_integration_authorization(
    package: dict[str, Any], control: dict[str, Any], prerequisites: list[GateResult]
) -> tuple[list[Finding], bool]:
    request = package.get("integration", {})
    completed = integration_completed(package, control)
    if not request.get("requested") and not completed:
        return [], False
    results: list[Finding] = []
    failed = [gate.gate for gate in prerequisites if gate.status != "PASS"]
    if failed:
        results.append(finding("INTEGRATION_PREREQUISITE_FAILED", "integration", "Integration authorization requires every upstream gate to pass: " + ", ".join(failed)))
    if not completed:
        results.extend(verify_receipt(package, control, request.get("receipt_id"), kind="INTEGRATION"))
    return results, True


def validate_deployment_artifacts(package: dict[str, Any], control: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    deployment = package.get("deployment", {})
    build = package.get("build", {})
    provenance = build.get("provenance", {})
    trusted_builders = set(control["trusted_builder_ids"])
    if provenance.get("builder_id") not in trusted_builders or not provenance.get("signature_verified"):
        results.append(finding("BUILD_PROVENANCE_INVALID", "build", "The artifact lacks verified provenance from a trusted build platform."))
    if provenance.get("subject_digest") != build.get("artifact_digest"):
        results.append(finding("DEPLOYMENT_ARTIFACT_MISMATCH", "deployment", "The deployed artifact is not the artifact named by verified build provenance."))
    if deployment.get("artifact_digest") != build.get("artifact_digest"):
        results.append(finding("DEPLOYMENT_ARTIFACT_MISMATCH", "deployment", "The deployment request points to a different artifact than the authorized build."))
    if deployment.get("rollback_artifact_digest") not in control["approved_rollback_artifacts"]:
        results.append(finding("ROLLBACK_ARTIFACT_UNAPPROVED", "deployment", "The rollback target is not a known approved artifact."))
    return results


def validate_deployment(
    package: dict[str, Any], control: dict[str, Any], integration_gate: GateResult
) -> tuple[list[Finding], bool]:
    deployment = package.get("deployment", {})
    if not deployment.get("requested"):
        return [], False
    results = verify_receipt(package, control, deployment.get("receipt_id"), kind="DEPLOYMENT")
    if integration_gate.status != "PASS" or not integration_completed(package, control):
        results.append(finding("DEPLOYMENT_PREREQUISITE_FAILED", "deployment", "Deployment requires a successfully consumed integration authorization for the exact source subject."))
    results.extend(validate_deployment_artifacts(package, control))
    return results, True


def validate_runtime(package: dict[str, Any], control: dict[str, Any]) -> tuple[list[Finding], bool]:
    runtime = package.get("runtime", {})
    if not runtime.get("observed"):
        return [], False
    results: list[Finding] = []
    if runtime.get("instrumentation_health") != "HEALTHY" or runtime.get("applicable_population", 0) <= 0:
        results.append(finding("RUNTIME_EVIDENCE_INCOMPLETE", "runtime", "Zero violations are uninterpretable without healthy instrumentation and a denominator."))
    contract = control.get("runtime_contract", {})
    if runtime.get("monitoring_window_id") != contract.get("monitoring_window_id"):
        results.append(finding("RUNTIME_WINDOW_STALE", "runtime", "Telemetry is not bound to the approved monitoring window."))
    expected_slices = set(contract.get("approved_population_slices", []))
    covered_slices = set(runtime.get("covered_population_slices", []))
    if (
        covered_slices != expected_slices
        or runtime.get("event_delivery") != contract.get("event_delivery_required")
        or runtime.get("applicable_population", 0) < contract.get("minimum_applicable_population", 1)
    ):
        results.append(finding("RUNTIME_COVERAGE_INCOMPLETE", "runtime", "Runtime evidence does not cover the approved rollout population with complete event delivery."))
    if runtime.get("invariant_violations", 0) > 0:
        results.append(finding("RUNTIME_INVARIANT_VIOLATION", "runtime", "A production invariant was violated."))
    computed_system_revision = canonical_system_digest(package.get("effective_ai_system_revision", {}).get("components", {}))
    if runtime.get("system_revision") != computed_system_revision:
        results.append(finding("RUNTIME_SUBJECT_MISMATCH", "runtime", "Telemetry describes a different effective AI system revision."))
    return results, True


def evaluate_delivery(package: dict[str, Any], control: dict[str, Any] | None = None) -> list[GateResult]:
    trusted = control or load_control_plane()
    gates = base_gate_results(package, trusted)
    integration_findings, integration_applicable = validate_integration_authorization(package, trusted, gates)
    integration_gate = _gate("integration_authorization", integration_findings, applicable=integration_applicable)
    deployment_findings, deployment_applicable = validate_deployment(package, trusted, integration_gate)
    runtime_findings, runtime_applicable = validate_runtime(package, trusted)
    gates.extend([
        integration_gate,
        _gate("deployment_authorization", deployment_findings, applicable=deployment_applicable),
        _gate("runtime_conformance", runtime_findings, applicable=runtime_applicable),
    ])
    if tuple(item.gate for item in gates) != REQUIRED_GATES:
        raise AssertionError("gate inventory changed")
    return gates


def aggregate(gates: list[GateResult]) -> str:
    if {gate.gate for gate in gates} != set(REQUIRED_GATES):
        return "BLOCKED_INCOMPLETE_GATE_SET"
    if any(gate.status == "BLOCK" for gate in gates):
        return "BLOCKED"
    if any(gate.status == "REVIEW" for gate in gates):
        return "REQUIRES_REVIEW"
    return "ELIGIBLE_FOR_INTEGRATION_REVIEW"


def finding_codes(gates: list[GateResult]) -> set[str]:
    return {item.code for gate in gates for item in gate.findings}


def consume_receipt(package: dict[str, Any], control: dict[str, Any], receipt_id: str, *, kind: str) -> dict[str, Any]:
    with _RECEIPT_LOCK:
        failures: list[Finding] = []
        prerequisites = base_gate_results(package, control)
        failed_gates = [gate.gate for gate in prerequisites if gate.status != "PASS"]
        if kind == "INTEGRATION" and failed_gates:
            failures.append(finding("INTEGRATION_PREREQUISITE_FAILED", "integration", "Receipt consumption requires passing upstream gates: " + ", ".join(failed_gates)))
        if kind == "DEPLOYMENT":
            if failed_gates or not integration_completed(package, control):
                failures.append(finding("DEPLOYMENT_PREREQUISITE_FAILED", "deployment", "Receipt consumption requires passing upstream gates and a durable exact-subject integration record."))
            failures.extend(validate_deployment_artifacts(package, control))
        failures.extend(verify_receipt(package, control, receipt_id, kind=kind))
        if failures:
            raise ValueError(failures[0].code)
        receipt = control["receipts"][receipt_id]
        receipt["state"] = "USED"
        receipt["version"] += 1
        if kind == "INTEGRATION":
            control.setdefault("completed_integrations", []).append(exact_transition_subject(package))
        return copy.deepcopy(receipt)


def classify_scenario(case: dict[str, Any]) -> str:
    package = load_reference()
    control = load_control_plane()
    for patch in case.get("patches", []):
        target = control if patch.get("target") == "control" else package
        apply_patch(target, patch)
    codes = finding_codes(evaluate_delivery(package, control))
    expected = case["expected"]
    return expected if expected in codes else "NO_MATCH"


def run_conformance_suite() -> dict[str, Any]:
    cases = read_json(ROOT / "conformance-suite.json")["cases"]
    passed = sum(classify_scenario(case) == case["expected"] for case in cases)
    return {"passed": passed, "total": len(cases), "claim": "fixture conformance, not production assurance"}


def _expanded_evaluation_cases() -> list[dict[str, Any]]:
    families = read_json(ROOT / "evaluation-cases.json")["families"]
    cases: list[dict[str, Any]] = []
    for family in families:
        for index, patch in enumerate(family["patches"], start=1):
            cases.append({"id": f"{family['id']}-{index}", "expected": family["expected"], "patches": patch if isinstance(patch, list) else [patch]})
    return cases


def mutation_findings(case: dict[str, Any]) -> set[str]:
    package = load_reference()
    control = load_control_plane()
    for patch in case["patches"]:
        target = control if patch.get("target") == "control" else package
        apply_patch(target, patch)
    return finding_codes(evaluate_delivery(package, control))


def run_evaluation() -> dict[str, Any]:
    cases = _expanded_evaluation_cases()
    passed = sum(case["expected"] in mutation_findings(case) for case in cases)
    return {"passed": passed, "total": len(cases), "claim": "labelled control mutations, not a benchmark"}


def serialize_gates(gates: list[GateResult]) -> list[dict[str, Any]]:
    return [{"gate": gate.gate, "status": gate.status, "findings": [asdict(item) for item in gate.findings]} for gate in gates]


def main() -> None:
    control = load_control_plane()
    reference = evaluate_delivery(load_reference(), control)
    unsafe = evaluate_delivery(load_candidate(), load_candidate_control())
    report = {
        "reference": {"decision": aggregate(reference), "gates": serialize_gates(reference)},
        "unsafe_candidate": {
            "decision": aggregate(unsafe),
            "technical_quality": next(item.status for item in unsafe if item.gate == "technical_quality"),
            "findings": sorted(finding_codes(unsafe)),
        },
        "conformance": run_conformance_suite(),
        "evaluation": run_evaluation(),
        "authority_boundary": "Agents propose and report; trusted controls validate and accountable owners authorize.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
