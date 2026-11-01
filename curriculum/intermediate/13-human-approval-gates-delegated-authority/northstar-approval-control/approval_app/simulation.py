"""Deterministic Course 23 scenarios and evaluation report."""
from __future__ import annotations

import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path
from typing import Callable

from .control_plane import ApprovalControlPlane
from .models import ActionSubject, ControlError, DelegationGrant

NOW = "2026-10-31T18:00:00Z"
LATER = "2026-10-31T18:10:00Z"
FUTURE = "2026-10-31T19:00:00Z"
DELEGATION_END = "2026-12-01T00:00:00Z"


def production_subject(**changes: str | None) -> ActionSubject:
    values = {
        "change_id": "CHG-2301",
        "action": "deploy",
        "resource": "underwriting-assistant-production",
        "environment": "production",
        "artifact_digest": "sha256:artifact-approved-2301",
        "specification_digest": "sha256:spec-approved-2301",
        "policy_revision": "APPROVAL-POLICY@4",
        "risk_tier": "CONSEQUENTIAL",
        "incident_id": None,
    }
    values.update(changes)
    return ActionSubject(**values)


def staging_subject(**changes: str | None) -> ActionSubject:
    values = {
        "change_id": "CHG-2302",
        "environment": "staging",
        "risk_tier": "MODERATE",
    }
    values.update(changes)
    return production_subject(**values)


def emergency_subject(**changes: str | None) -> ActionSubject:
    values = {
        "change_id": "CHG-EMERGENCY-42",
        "action": "disable_ai_classification",
        "resource": "underwriting-assistant-production",
        "environment": "production",
        "artifact_digest": "sha256:manual-review-routing-v7",
        "specification_digest": "sha256:incident-playbook-12",
        "policy_revision": "EMERGENCY-POLICY@3",
        "risk_tier": "CRITICAL",
        "incident_id": "INC-2500-42",
    }
    values.update(changes)
    return ActionSubject(**values)


def exception_subject(**changes: str | None) -> ActionSubject:
    values = {
        "change_id": "CHG-EXCEPTION-4",
        "action": "approve_low_risk_exception",
        "resource": "underwriting-platform",
        "environment": "n/a",
        "artifact_digest": "sha256:exception-4",
        "specification_digest": "sha256:security-standard-9",
        "policy_revision": "APPROVAL-POLICY@4",
        "risk_tier": "LOW",
        "incident_id": None,
    }
    values.update(changes)
    return ActionSubject(**values)


def _plane(root: Path, directory: str, name: str = "approval.db") -> ApprovalControlPlane:
    return ApprovalControlPlane(Path(directory) / name, root)


def _request(plane: ApprovalControlPlane, request_id: str, subject: ActionSubject, requester: str = "SESSION-REQUESTER", author: str = "agent-ai-a") -> None:
    plane.create_request(request_id, requester, author, subject, NOW)


def _approve_production(plane: ApprovalControlPlane, request_id: str, expires_at: str = FUTURE) -> tuple[str, str]:
    release = plane.decide(request_id, "SESSION-RELEASE", "release_authority", "APPROVED", NOW, expires_at)
    governance = plane.decide(request_id, "SESSION-GOVERNANCE", "ai_governance_owner", "APPROVED", NOW, expires_at)
    return release.receipt_ids[0], governance.receipt_ids[0]


def _expected_error(code: str, operation: Callable[[], object]) -> str:
    try:
        operation()
    except ControlError as exc:
        if exc.code != code:
            raise AssertionError(f"expected {code}, received {exc.code}") from exc
        return exc.code
    raise AssertionError(f"expected {code}, operation succeeded")


def _valid_exact_subject(root: Path, directory: str) -> dict:
    plane, subject = _plane(root, directory), production_subject()
    _request(plane, "REQ-VALID", subject)
    receipts = _approve_production(plane, "REQ-VALID")
    result = plane.execute("REQ-VALID", receipts, subject, "EXEC-VALID", LATER)
    return {"state": result.state, "operation_count": plane.operation_count("REQ-VALID")}


def _changed_artifact(root: Path, directory: str) -> str:
    plane, subject = _plane(root, directory), production_subject()
    _request(plane, "REQ-CHANGED", subject)
    receipts = _approve_production(plane, "REQ-CHANGED")
    changed = replace(subject, artifact_digest="sha256:artifact-not-approved")
    return _expected_error("APPROVAL_SUBJECT_MISMATCH", lambda: plane.execute("REQ-CHANGED", receipts, changed, "EXEC-CHANGED", LATER))


def _expired(root: Path, directory: str) -> str:
    plane, subject = _plane(root, directory), production_subject()
    _request(plane, "REQ-EXPIRED", subject)
    receipts = _approve_production(plane, "REQ-EXPIRED", expires_at=NOW)
    return _expected_error("APPROVAL_EXPIRED", lambda: plane.execute("REQ-EXPIRED", receipts, subject, "EXEC-EXPIRED", LATER))


def _revoked(root: Path, directory: str) -> str:
    plane, subject = _plane(root, directory), production_subject()
    _request(plane, "REQ-REVOKED", subject)
    receipts = _approve_production(plane, "REQ-REVOKED")
    plane.revoke_receipt(receipts[0], LATER)
    return _expected_error("APPROVAL_REVOKED", lambda: plane.execute("REQ-REVOKED", receipts, subject, "EXEC-REVOKED", LATER))


def _replayed(root: Path, directory: str) -> str:
    plane, subject = _plane(root, directory), production_subject()
    _request(plane, "REQ-REPLAY", subject)
    receipts = _approve_production(plane, "REQ-REPLAY")
    plane.execute("REQ-REPLAY", receipts, subject, "EXEC-FIRST", LATER)
    return _expected_error("APPROVAL_ALREADY_CONSUMED", lambda: plane.execute("REQ-REPLAY", receipts, subject, "EXEC-REPLAY", LATER))


def _forged(root: Path, directory: str) -> str:
    plane, subject = _plane(root, directory), production_subject()
    _request(plane, "REQ-FORGED", subject)
    return _expected_error("UNTRUSTED_RECEIPT", lambda: plane.execute("REQ-FORGED", ("APR-FORGED",), subject, "EXEC-FORGED", LATER))


def _wrong_resource(root: Path, directory: str) -> str:
    plane = _plane(root, directory)
    subject = production_subject(resource="payments-production")
    _request(plane, "REQ-RESOURCE", subject)
    return _expected_error("AUTHORITY_SCOPE_DENIED", lambda: plane.decide("REQ-RESOURCE", "SESSION-RELEASE", "release_authority", "APPROVED", NOW, FUTURE))


def _self_approval(root: Path, directory: str) -> str:
    plane, subject = _plane(root, directory), staging_subject()
    _request(plane, "REQ-SELF", subject, requester="SESSION-RELEASE", author="agent-ai-a")
    return _expected_error("SEPARATION_OF_DUTIES_VIOLATION", lambda: plane.decide("REQ-SELF", "SESSION-RELEASE", "release_authority", "APPROVED", NOW, FUTURE))


def _delegation_expansion(root: Path, directory: str) -> str:
    plane = _plane(root, directory)
    expanded = DelegationGrant(
        "DELEGATION-EXPANDED", "GRANT-SECURITY-EXCEPTION", "security-director-2", "security-lead-9",
        "security_exception_approver", frozenset({"approve_low_risk_exception"}),
        frozenset({"underwriting-platform", "all-enterprise-services"}), frozenset({"n/a"}),
        "CRITICAL", "2026-10-01T00:00:00Z", DELEGATION_END, False,
    )
    return _expected_error("DELEGATION_SCOPE_EXPANSION", lambda: plane.issue_delegation(expanded, "SESSION-SECURITY-DIRECTOR", NOW))


def _delegated_parent_revoked(root: Path, directory: str) -> str:
    plane, subject = _plane(root, directory), exception_subject()
    delegation = DelegationGrant(
        "DELEGATION-VALID", "GRANT-SECURITY-EXCEPTION", "security-director-2", "security-lead-9",
        "security_exception_approver", frozenset({"approve_low_risk_exception"}),
        frozenset({"underwriting-platform"}), frozenset({"n/a"}), "LOW",
        "2026-10-01T00:00:00Z", DELEGATION_END, False,
    )
    plane.issue_delegation(delegation, "SESSION-SECURITY-DIRECTOR", NOW)
    _request(plane, "REQ-DELEGATED", subject)
    receipt = plane.decide("REQ-DELEGATED", "SESSION-SECURITY-LEAD", "security_exception_approver", "APPROVED", NOW, FUTURE).receipt_ids
    plane.revoke_grant("GRANT-SECURITY-EXCEPTION")
    return _expected_error("DELEGATED_AUTHORITY_REVOKED", lambda: plane.execute("REQ-DELEGATED", receipt, subject, "EXEC-DELEGATED", LATER))


def concurrency_scenario(root: Path, directory: str) -> dict:
    plane, subject = _plane(root, directory), staging_subject()
    _request(plane, "REQ-CONCURRENT", subject)
    receipt = plane.decide("REQ-CONCURRENT", "SESSION-RELEASE", "release_authority", "APPROVED", NOW, FUTURE).receipt_ids

    def execute(execution_id: str) -> str:
        try:
            _plane(root, directory).execute("REQ-CONCURRENT", receipt, subject, execution_id, LATER)
            return "EXECUTED"
        except ControlError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(execute, ("EXEC-RACE-A", "EXEC-RACE-B")))
    result = {"outcomes": outcomes, "executed": outcomes.count("EXECUTED"), "operation_count": plane.operation_count("REQ-CONCURRENT")}
    if result["executed"] != 1 or result["operation_count"] != 1 or "APPROVAL_ALREADY_CONSUMED" not in outcomes:
        raise AssertionError(result)
    return result


def _emergency(root: Path, directory: str) -> dict:
    plane, subject = _plane(root, directory), emergency_subject()
    _request(plane, "REQ-EMERGENCY", subject)
    receipt = plane.decide("REQ-EMERGENCY", "SESSION-EMERGENCY", "emergency_responder", "APPROVED", NOW, FUTURE).receipt_ids
    result = plane.execute("REQ-EMERGENCY", receipt, subject, "EXEC-EMERGENCY", LATER)
    return {"state": result.state, "incident_id": subject.incident_id, "containment_action": subject.action}


SCENARIOS: tuple[tuple[str, Callable[[Path, str], object]], ...] = (
    ("valid_exact_artifact", _valid_exact_subject),
    ("changed_artifact", _changed_artifact),
    ("expired_approval", _expired),
    ("revoked_approval", _revoked),
    ("replayed_approval", _replayed),
    ("forged_approval", _forged),
    ("wrong_resource_authority", _wrong_resource),
    ("self_approval", _self_approval),
    ("delegation_scope_expansion", _delegation_expansion),
    ("parent_revoked_after_delegation", _delegated_parent_revoked),
    ("concurrent_single_use", concurrency_scenario),
    ("emergency_containment", _emergency),
)


def golden_scenarios(root: Path) -> list[dict]:
    results = []
    for name, scenario in SCENARIOS:
        with tempfile.TemporaryDirectory(prefix=f"course23-{name}-") as directory:
            evidence = scenario(root, directory)
        results.append({"scenario": name, "status": "PASS", "evidence": evidence})
    return results


def evaluation_cases(root: Path) -> list[dict]:
    cases: list[dict] = []

    def evaluate(name: str, expected: str, operation: Callable[[ApprovalControlPlane, ActionSubject], object], subject: ActionSubject | None = None) -> None:
        with tempfile.TemporaryDirectory(prefix=f"course23-eval-{name}-") as directory:
            plane = _plane(root, directory)
            try:
                operation(plane, subject or production_subject())
                actual = "ALLOWED"
            except ControlError as exc:
                actual = exc.code
            cases.append({"case": name, "expected": expected, "actual": actual, "status": "PASS" if actual == expected else "FAIL"})

    evaluate("unknown_session", "UNAUTHENTICATED_PRINCIPAL", lambda p, s: p.create_request("R", "SESSION-UNKNOWN", "agent", s, NOW))
    evaluate("old_policy_revision", "POLICY_REVISION_MISMATCH", lambda p, s: p.create_request("R", "SESSION-REQUESTER", "agent", replace(s, policy_revision="APPROVAL-POLICY@3"), NOW))
    evaluate("unresolved_risk", "APPROVAL_POLICY_UNRESOLVED", lambda p, s: p.create_request("R", "SESSION-REQUESTER", "agent", replace(s, risk_tier="CRITICAL"), NOW))
    evaluate("closed_incident", "EMERGENCY_AUTHORIZATION_DENIED", lambda p, s: p.create_request("R", "SESSION-REQUESTER", "agent", replace(s, incident_id="INC-2499-08"), NOW), emergency_subject())
    evaluate("missing_incident", "EMERGENCY_AUTHORIZATION_DENIED", lambda p, s: p.create_request("R", "SESSION-REQUESTER", "agent", replace(s, incident_id=None), NOW), emergency_subject())
    evaluate("emergency_wrong_resource", "EMERGENCY_SCOPE_VIOLATION", lambda p, s: p.create_request("R", "SESSION-REQUESTER", "agent", replace(s, resource="payments-production"), NOW), emergency_subject())
    evaluate("emergency_old_policy", "POLICY_REVISION_MISMATCH", lambda p, s: p.create_request("R", "SESSION-REQUESTER", "agent", replace(s, policy_revision="EMERGENCY-POLICY@2"), NOW), emergency_subject())
    evaluate("unknown_approver_role", "APPROVER_NOT_AUTHORIZED", lambda p, s: (_request(p, "R", s), p.decide("R", "SESSION-RELEASE", "invented_role", "APPROVED", NOW, FUTURE)))
    evaluate("outsider_without_grant", "AUTHORITY_SCOPE_DENIED", lambda p, s: (_request(p, "R", s), p.decide("R", "SESSION-OUTSIDER", "release_authority", "APPROVED", NOW, FUTURE)))
    evaluate("missing_dual_control", "REQUIRED_APPROVAL_MISSING", lambda p, s: (_request(p, "R", s), p.execute("R", p.decide("R", "SESSION-RELEASE", "release_authority", "APPROVED", NOW, FUTURE).receipt_ids, s, "E", LATER)))
    evaluate("implementation_author_approval", "SEPARATION_OF_DUTIES_VIOLATION", lambda p, s: (_request(p, "R", s, author="release-manager-17"), p.decide("R", "SESSION-RELEASE", "release_authority", "APPROVED", NOW, FUTURE)))
    evaluate("untrusted_receipt", "UNTRUSTED_RECEIPT", lambda p, s: (_request(p, "R", s), p.execute("R", ("fake",), s, "E", LATER)))

    if any(case["status"] != "PASS" for case in cases):
        raise AssertionError(cases)
    return cases


def audit_scenario(root: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="course23-audit-") as directory:
        plane, subject = _plane(root, directory), staging_subject()
        _request(plane, "REQ-AUDIT", subject)
        receipt = plane.decide("REQ-AUDIT", "SESSION-RELEASE", "release_authority", "APPROVED", NOW, FUTURE).receipt_ids
        plane.execute("REQ-AUDIT", receipt, subject, "EXEC-AUDIT", LATER)
        valid_before = plane.verify_audit_chain()
        with sqlite3.connect(plane.db_path) as connection:
            connection.execute("UPDATE audit_events SET reason_code = 'ALTERED' WHERE sequence = 1")
        valid_after = plane.verify_audit_chain()
    if not valid_before or valid_after:
        raise AssertionError("audit tampering was not detected")
    return {"valid_before_tamper": valid_before, "valid_after_tamper": valid_after, "tamper_detected": True}


def run_reference(root: Path) -> dict:
    golden = golden_scenarios(root)
    evaluations = evaluation_cases(root)
    audit = audit_scenario(root)
    return {
        "course": 23,
        "title": "Human Approval Gates and Delegated Authority",
        "decision": "ELIGIBLE_FOR_ACCOUNTABLE_REVIEW",
        "golden_scenarios": {"passed": len(golden), "total": len(golden), "results": golden},
        "evaluation_population": {"passed": len(evaluations), "total": len(evaluations), "results": evaluations},
        "audit_integrity": audit,
        "reference_subject": asdict(production_subject()),
        "non_authorities": [
            "The report does not approve a production deployment.",
            "The teaching policy is not a substitute for an enterprise identity or authority system.",
            "External side effects require idempotency and reconciliation beyond this local transaction boundary."
        ],
    }
