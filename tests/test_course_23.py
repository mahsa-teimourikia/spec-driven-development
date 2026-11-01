"""Focused verification for Course 23 human approval control."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum/intermediate/13-human-approval-gates-delegated-authority"
SCENARIO = LESSON / "northstar-approval-control"
sys.path.insert(0, str(SCENARIO))

from approval_app.control_plane import ApprovalControlPlane  # noqa: E402
from approval_app.models import ControlError, DelegationGrant  # noqa: E402
from approval_app.simulation import (  # noqa: E402
    DELEGATION_END, FUTURE, LATER, NOW, audit_scenario, concurrency_scenario,
    emergency_subject, evaluation_cases, exception_subject, golden_scenarios,
    production_subject, run_reference, staging_subject,
)


class Course23Tests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="course23-test-")
        self.plane = ApprovalControlPlane(Path(self.directory.name) / "approval.db", SCENARIO)

    def tearDown(self):
        self.directory.cleanup()

    def assertControlError(self, code, operation):
        with self.assertRaises(ControlError) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def request(self, request_id="REQ-TEST", subject=None, requester="SESSION-REQUESTER", author="agent-ai-a"):
        subject = subject or production_subject()
        self.plane.create_request(request_id, requester, author, subject, NOW)
        return subject

    def approve_production(self, request_id="REQ-TEST", expires=FUTURE):
        release = self.plane.decide(request_id, "SESSION-RELEASE", "release_authority", "APPROVED", NOW, expires)
        governance = self.plane.decide(request_id, "SESSION-GOVERNANCE", "ai_governance_owner", "APPROVED", NOW, expires)
        return release.receipt_ids + governance.receipt_ids

    def test_subject_digest_changes_with_artifact(self):
        subject = production_subject()
        self.assertNotEqual(subject.digest, replace(subject, artifact_digest="sha256:changed").digest)

    def test_unknown_session_is_not_identity(self):
        self.assertControlError("UNAUTHENTICATED_PRINCIPAL", lambda: self.plane.authenticate("release-manager-17"))

    def test_production_requires_two_roles(self):
        self.assertEqual(set(self.plane.required_roles(production_subject())), {"release_authority", "ai_governance_owner"})

    def test_staging_requires_one_role(self):
        self.assertEqual(self.plane.required_roles(staging_subject()), ("release_authority",))

    def test_policy_revision_is_subject_bound(self):
        stale = replace(production_subject(), policy_revision="APPROVAL-POLICY@3")
        self.assertControlError("POLICY_REVISION_MISMATCH", lambda: self.plane.required_roles(stale))

    def test_requester_cannot_approve(self):
        self.request(requester="SESSION-RELEASE")
        self.assertControlError("SEPARATION_OF_DUTIES_VIOLATION", lambda: self.plane.decide("REQ-TEST", "SESSION-RELEASE", "release_authority", "APPROVED", NOW, FUTURE))

    def test_implementation_author_cannot_approve(self):
        self.request(author="release-manager-17")
        self.assertControlError("SEPARATION_OF_DUTIES_VIOLATION", lambda: self.plane.decide("REQ-TEST", "SESSION-RELEASE", "release_authority", "APPROVED", NOW, FUTURE))

    def test_role_does_not_authorize_wrong_resource(self):
        self.request(subject=production_subject(resource="payments-production"))
        self.assertControlError("AUTHORITY_SCOPE_DENIED", lambda: self.plane.decide("REQ-TEST", "SESSION-RELEASE", "release_authority", "APPROVED", NOW, FUTURE))

    def test_outsider_has_no_authority(self):
        self.request()
        self.assertControlError("AUTHORITY_SCOPE_DENIED", lambda: self.plane.decide("REQ-TEST", "SESSION-OUTSIDER", "release_authority", "APPROVED", NOW, FUTURE))

    def test_one_receipt_cannot_satisfy_dual_control(self):
        subject = self.request()
        receipt = self.plane.decide("REQ-TEST", "SESSION-RELEASE", "release_authority", "APPROVED", NOW, FUTURE).receipt_ids
        self.assertControlError("REQUIRED_APPROVAL_MISSING", lambda: self.plane.execute("REQ-TEST", receipt, subject, "EXEC", LATER))

    def test_exact_approved_subject_executes_once(self):
        subject = self.request()
        receipts = self.approve_production()
        decision = self.plane.execute("REQ-TEST", receipts, subject, "EXEC", LATER)
        self.assertEqual((decision.state, self.plane.operation_count("REQ-TEST")), ("EXECUTED", 1))

    def test_changed_artifact_is_denied(self):
        subject = self.request()
        receipts = self.approve_production()
        changed = replace(subject, artifact_digest="sha256:not-approved")
        self.assertControlError("APPROVAL_SUBJECT_MISMATCH", lambda: self.plane.execute("REQ-TEST", receipts, changed, "EXEC", LATER))

    def test_expired_receipt_is_denied(self):
        subject = self.request()
        receipts = self.approve_production(expires=NOW)
        self.assertControlError("APPROVAL_EXPIRED", lambda: self.plane.execute("REQ-TEST", receipts, subject, "EXEC", LATER))

    def test_revoked_receipt_is_denied(self):
        subject = self.request()
        receipts = self.approve_production()
        self.plane.revoke_receipt(receipts[0], LATER)
        self.assertControlError("APPROVAL_REVOKED", lambda: self.plane.execute("REQ-TEST", receipts, subject, "EXEC", LATER))

    def test_receipt_replay_is_denied(self):
        subject = self.request()
        receipts = self.approve_production()
        self.plane.execute("REQ-TEST", receipts, subject, "EXEC-1", LATER)
        self.assertControlError("APPROVAL_ALREADY_CONSUMED", lambda: self.plane.execute("REQ-TEST", receipts, subject, "EXEC-2", LATER))

    def test_forged_receipt_reference_is_denied(self):
        subject = self.request()
        self.assertControlError("UNTRUSTED_RECEIPT", lambda: self.plane.execute("REQ-TEST", ("APR-FORGED",), subject, "EXEC", LATER))

    def valid_delegation(self):
        return DelegationGrant(
            "DELEGATION-TEST", "GRANT-SECURITY-EXCEPTION", "security-director-2", "security-lead-9",
            "security_exception_approver", frozenset({"approve_low_risk_exception"}),
            frozenset({"underwriting-platform"}), frozenset({"n/a"}), "LOW",
            "2026-10-01T00:00:00Z", DELEGATION_END, False,
        )

    def test_valid_attenuated_delegation_can_approve(self):
        subject = exception_subject()
        self.plane.issue_delegation(self.valid_delegation(), "SESSION-SECURITY-DIRECTOR", NOW)
        self.request(subject=subject)
        decision = self.plane.decide("REQ-TEST", "SESSION-SECURITY-LEAD", "security_exception_approver", "APPROVED", NOW, FUTURE)
        self.assertEqual(decision.state, "APPROVED")

    def test_delegation_cannot_raise_risk(self):
        expanded = replace(self.valid_delegation(), max_risk="CRITICAL")
        self.assertControlError("DELEGATION_SCOPE_EXPANSION", lambda: self.plane.issue_delegation(expanded, "SESSION-SECURITY-DIRECTOR", NOW))

    def test_delegation_cannot_add_resource(self):
        expanded = replace(self.valid_delegation(), resources=frozenset({"underwriting-platform", "payments"}))
        self.assertControlError("DELEGATION_SCOPE_EXPANSION", lambda: self.plane.issue_delegation(expanded, "SESSION-SECURITY-DIRECTOR", NOW))

    def test_parent_revocation_invalidates_delegated_execution(self):
        subject = exception_subject()
        self.plane.issue_delegation(self.valid_delegation(), "SESSION-SECURITY-DIRECTOR", NOW)
        self.request(subject=subject)
        receipt = self.plane.decide("REQ-TEST", "SESSION-SECURITY-LEAD", "security_exception_approver", "APPROVED", NOW, FUTURE).receipt_ids
        self.plane.revoke_grant("GRANT-SECURITY-EXCEPTION")
        self.assertControlError("DELEGATED_AUTHORITY_REVOKED", lambda: self.plane.execute("REQ-TEST", receipt, subject, "EXEC", LATER))

    def test_emergency_requires_active_incident(self):
        missing = replace(emergency_subject(), incident_id=None)
        self.assertControlError("EMERGENCY_AUTHORIZATION_DENIED", lambda: self.plane.required_roles(missing))

    def test_emergency_is_resource_scoped(self):
        wrong = replace(emergency_subject(), resource="payments-production")
        self.assertControlError("EMERGENCY_SCOPE_VIOLATION", lambda: self.plane.required_roles(wrong))

    def test_emergency_uses_distinct_policy_revision(self):
        wrong = replace(emergency_subject(), policy_revision="APPROVAL-POLICY@4")
        self.assertControlError("POLICY_REVISION_MISMATCH", lambda: self.plane.required_roles(wrong))

    def test_concurrency_has_exactly_one_winner(self):
        result = concurrency_scenario(SCENARIO, self.directory.name)
        self.assertEqual((result["executed"], result["operation_count"]), (1, 1))

    def test_audit_chain_detects_mutation(self):
        result = audit_scenario(SCENARIO)
        self.assertTrue(result["valid_before_tamper"] and result["tamper_detected"])
        self.assertFalse(result["valid_after_tamper"])

    def test_golden_population_is_twelve(self):
        results = golden_scenarios(SCENARIO)
        self.assertEqual((len(results), sum(item["status"] == "PASS" for item in results)), (12, 12))

    def test_evaluation_population_is_twelve(self):
        results = evaluation_cases(SCENARIO)
        self.assertEqual((len(results), sum(item["status"] == "PASS" for item in results)), (12, 12))

    def test_report_stops_at_accountable_review(self):
        report = run_reference(SCENARIO)
        self.assertEqual(report["decision"], "ELIGIBLE_FOR_ACCOUNTABLE_REVIEW")
        self.assertTrue(any("does not approve" in item for item in report["non_authorities"]))

    def test_scenario_labels_are_not_evaluator_inputs(self):
        source = (SCENARIO / "approval_app/simulation.py").read_text(encoding="utf-8")
        self.assertNotIn("scenarios/", source)
        self.assertNotIn("evaluation-cases.json", source)

    def test_starter_has_six_decisions_and_reference_has_no_todo(self):
        starter = (SCENARIO / "workshop/starter/approval-design.json").read_text(encoding="utf-8")
        reference = (SCENARIO / "reference/approval-design.json").read_text(encoding="utf-8")
        self.assertEqual(starter.count("TODO"), 6)
        self.assertNotIn("TODO", reference)

    def test_notebook_imports_reusable_module_and_is_clean(self):
        notebook = json.loads((SCENARIO / "human_approval_gates.ipynb").read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
        self.assertIn("from approval_app.simulation import", source)
        self.assertIn("run_reference(ROOT)", source)
        self.assertTrue(all(not cell.get("outputs") for cell in notebook["cells"] if cell.get("cell_type") == "code"))


if __name__ == "__main__":
    unittest.main()
