#!/usr/bin/env python3
"""Deterministic Course 15 lab: connect SDD artifacts to trusted delivery gates."""

from __future__ import annotations

import copy
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
    return results


def validate_implementation(package: dict[str, Any], control: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    manifest = package.get("change_manifest", {})
    changed_paths = set(package.get("pull_request", {}).get("changed_paths", []))
    allowed = set(manifest.get("authorized_paths", []))
    protected = set(control["protected_paths"])
    if changed_paths - allowed or changed_paths & protected:
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
    for record in package.get("evidence_manifest", {}).get("records", []):
        claim_id = record.get("claim_id", "unknown")
        if record.get("producer") not in trusted or not record.get("independent"):
            results.append(finding("UNTRUSTED_EVIDENCE_PRODUCER", claim_id, "The evidence was not produced by an approved independent verifier."))
            continue
        expected_subject = {
            "change_id": manifest.get("change_id"),
            "commit": package.get("pull_request", {}).get("head_sha"),
            "specification_revision": manifest.get("specification_revision"),
            "system_revision": package.get("effective_ai_system_revision", {}).get("digest"),
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
    observed = package.get("control_provenance", {})
    expected = control["validator"]
    if observed != expected:
        return [finding("CONTROL_PROVENANCE_INVALID", "validator", "The decision was not produced by the trusted default-branch validator revision.")]
    if any(path.startswith(".github/workflows/") or path.startswith("delivery-control/") for path in package.get("pull_request", {}).get("changed_paths", [])):
        return [finding("CONTROL_PROVENANCE_INVALID", "pull-request", "A PR cannot alter the controls that judge that same PR.")]
    return []


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
    expected = {
        "change_id": package["change_manifest"]["change_id"],
        "commit": package["pull_request"]["head_sha"],
        "specification_revision": package["change_manifest"]["specification_revision"],
        "system_revision": package["effective_ai_system_revision"]["digest"],
    }
    if kind == "DEPLOYMENT":
        expected.update({
            "artifact_digest": package.get("build", {}).get("artifact_digest"),
            "environment": package.get("deployment", {}).get("environment"),
        })
    if receipt.get("subject") != expected:
        results.append(finding(f"INVALID_{kind}_AUTHORIZATION", receipt_id, "The receipt is not bound to the exact transition subject."))
    return results


def validate_integration_authorization(package: dict[str, Any], control: dict[str, Any]) -> tuple[list[Finding], bool]:
    request = package.get("integration", {})
    if not request.get("requested"):
        return [], False
    return verify_receipt(package, control, request.get("receipt_id"), kind="INTEGRATION"), True


def validate_deployment(package: dict[str, Any], control: dict[str, Any]) -> tuple[list[Finding], bool]:
    deployment = package.get("deployment", {})
    if not deployment.get("requested"):
        return [], False
    results = verify_receipt(package, control, deployment.get("receipt_id"), kind="DEPLOYMENT")
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
    return results, True


def validate_runtime(package: dict[str, Any], _control: dict[str, Any]) -> tuple[list[Finding], bool]:
    runtime = package.get("runtime", {})
    if not runtime.get("observed"):
        return [], False
    results: list[Finding] = []
    if runtime.get("instrumentation_health") != "HEALTHY" or runtime.get("applicable_population", 0) <= 0:
        results.append(finding("RUNTIME_EVIDENCE_INCOMPLETE", "runtime", "Zero violations are uninterpretable without healthy instrumentation and a denominator."))
    if runtime.get("invariant_violations", 0) > 0:
        results.append(finding("RUNTIME_INVARIANT_VIOLATION", "runtime", "A production invariant was violated."))
    if runtime.get("system_revision") != package.get("effective_ai_system_revision", {}).get("digest"):
        results.append(finding("RUNTIME_SUBJECT_MISMATCH", "runtime", "Telemetry describes a different effective AI system revision."))
    return results, True


def evaluate_delivery(package: dict[str, Any], control: dict[str, Any] | None = None) -> list[GateResult]:
    trusted = control or load_control_plane()
    integration_findings, integration_applicable = validate_integration_authorization(package, trusted)
    deployment_findings, deployment_applicable = validate_deployment(package, trusted)
    runtime_findings, runtime_applicable = validate_runtime(package, trusted)
    gates = [
        _gate("specification_readiness", validate_specification(package, trusted)),
        _gate("implementation_conformance", validate_implementation(package, trusted)),
        _gate("technical_quality", validate_technical_quality(package, trusted)),
        _gate("evidence_integrity", validate_evidence(package, trusted)),
        _gate("control_provenance", validate_control_provenance(package, trusted)),
        _gate("integration_readiness", validate_integration_readiness(package, trusted)),
        _gate("integration_authorization", integration_findings, applicable=integration_applicable),
        _gate("deployment_authorization", deployment_findings, applicable=deployment_applicable),
        _gate("runtime_conformance", runtime_findings, applicable=runtime_applicable),
    ]
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
        failures = verify_receipt(package, control, receipt_id, kind=kind)
        if failures:
            raise ValueError(failures[0].code)
        receipt = control["receipts"][receipt_id]
        receipt["state"] = "USED"
        receipt["version"] += 1
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
    unsafe = evaluate_delivery(load_candidate(), control)
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
