"""Executed golden paths and adversarial mutations for Course 25."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from typing import Callable

from .control_plane import GovernanceControlPlane
from .models import Evidence, GovernanceError
from .registry import load_json, sign_evidence

NOW = "2026-11-01T16:00:00Z"
LATER = "2026-11-01T17:00:00Z"
FUTURE = "2026-12-01T00:00:00Z"


def harness_keys(root: Path) -> dict[str, str]:
    return load_json(root / "trusted-harness/verification-keys.json")


def make_plane(root: Path, database: Path) -> GovernanceControlPlane:
    return GovernanceControlPlane(root, database, harness_keys(root))


def evidence_for(plane: GovernanceControlPlane, kind: str, *, expires_at: str = FUTURE) -> tuple[Evidence, str]:
    subject = plane.subject("AI-UC-2500")
    producers = {
        "model_evaluation": "northstar-evaluation-service",
        "security": "northstar-security-service",
        "privacy": "northstar-privacy-service",
        "human_oversight": "northstar-review-service",
    }
    claims = {
        "model_evaluation": "MODEL-QUALITY-CLASSIFICATION",
        "security": "SECURITY-AGENT-BOUNDARY",
        "privacy": "PRIVACY-DATA-HANDLING",
        "human_oversight": "OVERSIGHT-HUMAN-REVIEW",
    }
    record = Evidence(
        f"EVD-2500-{kind.upper()}", claims[kind], kind,
        plane.subject_digest("AI-UC-2500"),
        producers[kind], "PASS", NOW, expires_at,
        {
            "model_revision": subject["model"]["revision"],
            "agent_revision": subject["agent"]["revision"],
            "policy_version": plane.policy["version"],
        },
        {"population": "northstar-labelled-fixture", "independent": True},
    )
    key_id = plane.trust["evidence_producers"][record.producer]["key_id"]
    return record, sign_evidence(record, plane.keys[key_id])


def runtime_violation_for(plane: GovernanceControlPlane) -> tuple[Evidence, str]:
    subject = plane.subject("AI-UC-2500")
    record = Evidence(
        "OBS-2500-REVIEW-BYPASS", "RUNTIME-HUMAN-REVIEW-BYPASS", "runtime_violation",
        plane.subject_digest("AI-UC-2500"), "northstar-runtime-monitor", "FAIL",
        NOW, FUTURE,
        {
            "model_revision": subject["model"]["revision"],
            "agent_revision": subject["agent"]["revision"],
            "policy_version": plane.policy["version"],
        },
        {
            "protected_invariant": "HUMAN_REVIEW_BYPASS",
            "deployment_id": "DEPLOY-AI-2500-PROD-1",
            "environment": "production",
            "observation_window": {
                "start": "2026-11-01T15:00:00Z",
                "end": "2026-11-01T15:59:00Z"
            },
            "population": 12,
            "violations": 1,
            "event_ids": ["EVENT-REVIEW-BYPASS-001"]
        },
    )
    key_id = plane.trust["evidence_producers"][record.producer]["key_id"]
    return record, sign_evidence(record, plane.keys[key_id])


def reinstatement_for(plane: GovernanceControlPlane) -> tuple[Evidence, str]:
    subject = plane.subject("AI-UC-2500")
    record = Evidence(
        "EVD-2500-REINSTATEMENT-001", "REINSTATEMENT-HUMAN-REVIEW", "reinstatement",
        plane.subject_digest("AI-UC-2500"), "northstar-review-service", "PASS",
        LATER, FUTURE,
        {
            "model_revision": subject["model"]["revision"],
            "agent_revision": subject["agent"]["revision"],
            "policy_version": plane.policy["version"],
        },
        {
            "protected_invariant": "HUMAN_REVIEW_BYPASS",
            "deployment_id": "DEPLOY-AI-2500-PROD-1",
            "remediation_id": "REM-2500-001",
            "verification_summary": "Human-review routing restored and independently verified."
        },
    )
    key_id = plane.trust["evidence_producers"][record.producer]["key_id"]
    return record, sign_evidence(record, plane.keys[key_id])


def register_required(plane: GovernanceControlPlane, *, omit: set[str] | None = None) -> None:
    for claim_id in plane.policy["required_claims"]["CONSEQUENTIAL"]:
        kind = plane.policy["claim_catalog"][claim_id]["kind"]
        if kind in (omit or set()):
            continue
        record, signature = evidence_for(plane, kind)
        plane.register_evidence("AI-UC-2500", record, signature, NOW)


def reference_operation(root: Path, database: Path) -> dict:
    plane = make_plane(root, database)
    register_required(plane)
    eligibility = plane.evaluate("AI-UC-2500", LATER)
    receipt = plane.approve(
        "AI-UC-2500", eligibility.subject_digest, "SESSION-AI-GOV",
        "operate_bounded_use_case", LATER, FUTURE,
    )
    allowed = plane.authorize_operation(receipt.receipt_id, "OP-AI-2500-001", "SESSION-EXECUTOR", LATER)
    impact = plane.change_impact("AI-UC-2500", {"model_revision": "model-v13"})
    result = {
        "eligibility": eligibility.payload(),
        "operation": allowed.payload(),
        "change_impact": impact,
        "approval": {
            "receipt_id": receipt.receipt_id,
            "subject_digest": receipt.subject_digest,
            "policy_version": receipt.policy_version,
            "principal_id": receipt.principal_id,
        },
    }
    plane.close()
    return result


def _scenario(root: Path, mutate: Callable[[GovernanceControlPlane], None] | None = None,
              omit: set[str] | None = None, *, register: bool = True
              ) -> tuple[GovernanceControlPlane, tempfile.TemporaryDirectory]:
    temporary = tempfile.TemporaryDirectory(prefix="course25-")
    plane = make_plane(root, Path(temporary.name) / "governance.db")
    if mutate:
        mutate(plane)
    if register:
        register_required(plane, omit=omit)
    return plane, temporary


def run_golden_scenarios(root: Path) -> dict:
    results: list[dict] = []

    def record(name: str, passed: bool, observed: str) -> None:
        results.append({"name": name, "passed": passed, "observed": observed})

    with tempfile.TemporaryDirectory(prefix="course25-reference-") as directory:
        report = reference_operation(root, Path(directory) / "governance.db")
        record("exact bounded use", report["operation"]["decision"] == "ALLOWED", report["operation"]["decision"])

    plane, temp = _scenario(root, omit={"privacy"})
    decision = plane.evaluate("AI-UC-2500", LATER)
    record("missing privacy evidence", decision.decision == "INSUFFICIENT_EVIDENCE", decision.decision)
    plane.close(); temp.cleanup()

    plane, temp = _scenario(root, lambda p: p.models["MODEL-012"].update(status="REVOKED"))
    decision = plane.evaluate("AI-UC-2500", LATER)
    record("revoked model", "MODEL_NOT_APPROVED" in decision.findings, decision.decision)
    plane.close(); temp.cleanup()

    plane, temp = _scenario(root, lambda p: p.use_cases["AI-UC-2500"].update(risk_tier="LOW"))
    decision = plane.evaluate("AI-UC-2500", LATER)
    record("self-downgraded risk", "RISK_TIER_MISMATCH" in decision.findings, decision.decision)
    plane.close(); temp.cleanup()

    plane, temp = _scenario(root, lambda p: p.use_cases["AI-UC-2500"].update(human_oversight="UNVERIFIED"))
    decision = plane.evaluate("AI-UC-2500", LATER)
    record("missing human oversight", "HUMAN_OVERSIGHT_UNVERIFIED" in decision.findings, decision.decision)
    plane.close(); temp.cleanup()

    def add_mutation(p: GovernanceControlPlane) -> None:
        p.agents["AGENT-2500"]["tool_ids"].append("TOOL-UNDERWRITING-MUTATE")
    plane, temp = _scenario(root, add_mutation)
    decision = plane.evaluate("AI-UC-2500", LATER)
    record("unauthorized autonomy", "UNAUTHORIZED_AUTONOMY" in decision.findings, decision.decision)
    plane.close(); temp.cleanup()

    plane, temp = _scenario(root, lambda p: p.use_cases["AI-UC-2500"].update(data_residency="UNKNOWN"))
    decision = plane.evaluate("AI-UC-2500", LATER)
    record("unknown residency", "DATA_RESIDENCY_UNKNOWN" in decision.findings, decision.decision)
    plane.close(); temp.cleanup()

    plane, temp = _scenario(root)
    decision = plane.evaluate("AI-UC-2500", LATER)
    try:
        plane.approve("AI-UC-2500", "sha256:wrong", "SESSION-AI-GOV", "operate_bounded_use_case", LATER, FUTURE)
        code = "NOT_REJECTED"
    except GovernanceError as exc:
        code = exc.code
    record("wrong approval subject", code == "APPROVAL_SUBJECT_MISMATCH", code)
    plane.close(); temp.cleanup()

    plane, temp = _scenario(root)
    decision = plane.evaluate("AI-UC-2500", LATER)
    try:
        plane.approve("AI-UC-2500", decision.subject_digest, "SESSION-AGENT", "operate_bounded_use_case", LATER, FUTURE)
        code = "NOT_REJECTED"
    except GovernanceError as exc:
        code = exc.code
    record("agent self approval", code == "APPROVER_NOT_AUTHORIZED", code)
    plane.close(); temp.cleanup()

    plane, temp = _scenario(root)
    decision = plane.evaluate("AI-UC-2500", LATER)
    receipt = plane.approve("AI-UC-2500", decision.subject_digest, "SESSION-AI-GOV", "operate_bounded_use_case", LATER, FUTURE)
    plane.policy["version"] = "ENTERPRISE-AI-POLICY@6"
    try:
        plane.authorize_operation(receipt.receipt_id, "OP-STALE", "SESSION-EXECUTOR", LATER)
        code = "NOT_REJECTED"
    except GovernanceError as exc:
        code = exc.code
    record("policy change invalidates approval", code in {"APPROVAL_POLICY_STALE", "APPROVAL_SUBJECT_STALE"}, code)
    plane.close(); temp.cleanup()

    plane, temp = _scenario(root)
    impact = plane.change_impact("AI-UC-2500", {"model_revision": "model-v13"})
    record("model change reassessment", impact["state"] == "REASSESSMENT_REQUIRED", impact["state"])
    plane.close(); temp.cleanup()

    plane, temp = _scenario(root)
    impact = plane.change_impact("AI-UC-2500", {"agent_tools": "expanded"})
    record("tool change reassessment", "authorization" in impact["required_reassessment"], impact["state"])
    plane.close(); temp.cleanup()

    plane, temp = _scenario(root)
    observation, signature = runtime_violation_for(plane)
    suspension = plane.suspend_on_violation("AI-UC-2500", observation, signature, LATER)
    record("protected runtime violation", suspension.decision == "SUSPENDED", suspension.decision)
    plane.close(); temp.cleanup()

    return {"passed": sum(item["passed"] for item in results), "total": len(results), "results": results}


def run_adversarial_evaluations(root: Path) -> dict:
    """Execute every labelled mutation independently and compare actual outcomes."""
    cases = load_json(root / "evaluation-cases.json")
    results: list[dict] = []
    for case in cases:
        plane, temporary = _scenario(root, register=False)
        scenario = case["scenario"]
        try:
            # Mutate before evidence production so the evaluator tests the intended
            # control rather than accidentally passing because evidence is stale.
            if scenario == "revoked model":
                plane.models["MODEL-012"]["status"] = "REVOKED"
            elif scenario == "self-downgraded risk":
                plane.use_cases["AI-UC-2500"]["risk_tier"] = "LOW"
            elif scenario == "missing human oversight":
                plane.use_cases["AI-UC-2500"]["human_oversight"] = "UNVERIFIED"
            elif scenario == "unauthorized autonomy":
                plane.agents["AGENT-2500"]["tool_ids"].append("TOOL-UNDERWRITING-MUTATE")
            elif scenario == "unknown residency":
                plane.use_cases["AI-UC-2500"]["data_residency"] = "UNKNOWN"
            elif scenario == "combined lifecycle and residency mutation":
                plane.agents["AGENT-2500"]["status"] = "REVOKED"
                plane.tools["TOOL-DOCUMENT-READ"]["status"] = "DISABLED"
                plane.use_cases["AI-UC-2500"]["data_residency"] = "UNKNOWN"

            if scenario == "model change reassessment":
                impact = plane.change_impact("AI-UC-2500", {"model_revision": "model-v13"})
                actual_decision = impact["state"]
                actual_findings = sorted(impact["required_reassessment"])
            elif scenario == "tool change reassessment":
                impact = plane.change_impact("AI-UC-2500", {"agent_tools": "expanded"})
                actual_decision = impact["state"]
                actual_findings = sorted(impact["required_reassessment"])
            elif scenario == "protected runtime violation":
                observation, signature = runtime_violation_for(plane)
                decision = plane.suspend_on_violation("AI-UC-2500", observation, signature, LATER)
                actual_decision, actual_findings = decision.decision, sorted(decision.findings)
            else:
                omit = {"privacy"} if scenario == "missing privacy evidence" else set()
                register_required(plane, omit=omit)
                decision = plane.evaluate("AI-UC-2500", LATER)
                if scenario in {"exact bounded use", "wrong approval subject", "agent self approval",
                                "policy change invalidates approval"}:
                    if scenario == "wrong approval subject":
                        plane.approve("AI-UC-2500", "sha256:wrong", "SESSION-AI-GOV",
                                      "operate_bounded_use_case", LATER, FUTURE)
                    elif scenario == "agent self approval":
                        plane.approve("AI-UC-2500", decision.subject_digest, "SESSION-AGENT",
                                      "operate_bounded_use_case", LATER, FUTURE)
                    else:
                        receipt = plane.approve(
                            "AI-UC-2500", decision.subject_digest, "SESSION-AI-GOV",
                            "operate_bounded_use_case", LATER, FUTURE,
                        )
                        if scenario == "policy change invalidates approval":
                            plane.policy["version"] = "ENTERPRISE-AI-POLICY@6"
                        decision = plane.authorize_operation(
                            receipt.receipt_id, f"OP-{case['id']}", "SESSION-EXECUTOR", LATER
                        )
                        actual_decision, actual_findings = decision.decision, sorted(decision.findings)
                else:
                    actual_decision, actual_findings = decision.decision, sorted(decision.findings)
        except GovernanceError as exc:
            actual_decision, actual_findings = "ERROR", [exc.code]
        finally:
            plane.close()
            temporary.cleanup()
        expected_findings = sorted(case["expected_findings"])
        results.append({
            "id": case["id"],
            "passed": (actual_decision == case["expected_decision"]
                       and actual_findings == expected_findings),
            "expected": {"decision": case["expected_decision"], "findings": expected_findings},
            "observed": {"decision": actual_decision, "findings": actual_findings},
        })
    return {"passed": sum(item["passed"] for item in results), "total": len(results), "results": results}


def run_reference(root: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="course25-report-") as directory:
        reference = reference_operation(root, Path(directory) / "governance.db")
    golden = run_golden_scenarios(root)
    adversarial = run_adversarial_evaluations(root)
    return {
        "course": 25,
        "decision": "ELIGIBLE_FOR_ACCOUNTABLE_REVIEW",
        "reference": reference,
        "golden_scenarios": golden,
        "adversarial_evaluations": adversarial,
        "non_authorities": [
            "The fixture does not grant organizational or legal approval.",
            "HMAC teaching records are not production workload identity.",
            "The illustrative risk taxonomy is not a regulatory classification.",
            "An ALLOWED result authorizes only the exact local bounded operation.",
        ],
    }
