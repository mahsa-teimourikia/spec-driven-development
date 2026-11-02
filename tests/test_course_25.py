"""Focused verification for Course 25 enterprise AI governance."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum/advanced/01-enterprise-ai-governance-agentic-software-development"
SCENARIO = LESSON / "northstar-ai-governance"
sys.path.insert(0, str(SCENARIO))

from governance_app.models import Evidence, GovernanceError  # noqa: E402
from governance_app.registry import sign_evidence  # noqa: E402
from governance_app.simulation import (  # noqa: E402
    FUTURE, LATER, NOW, evidence_for, make_plane, register_required, runtime_violation_for,
    run_adversarial_evaluations, run_golden_scenarios, run_reference,
)


class Course25Tests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="course25-test-")
        self.plane = make_plane(SCENARIO, Path(self.directory.name) / "governance.db")

    def tearDown(self):
        self.plane.close()
        self.directory.cleanup()

    def assertGovernanceError(self, code, operation):
        with self.assertRaises(GovernanceError) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def eligible(self):
        register_required(self.plane)
        decision = self.plane.evaluate("AI-UC-2500", LATER)
        self.assertEqual(decision.decision, "ELIGIBLE_FOR_ACCOUNTABLE_APPROVAL")
        return decision

    def receipt(self):
        decision = self.eligible()
        return self.plane.approve(
            "AI-UC-2500", decision.subject_digest, "SESSION-AI-GOV",
            "operate_bounded_use_case", LATER, FUTURE,
        )

    def test_use_case_relationships_resolve(self):
        subject = self.plane.subject("AI-UC-2500")
        self.assertEqual(subject["model"]["id"], "MODEL-012")
        self.assertEqual(subject["agent"]["id"], "AGENT-2500")
        self.assertEqual(len(subject["tools"]), 2)

    def test_unknown_use_case_is_rejected(self):
        self.assertGovernanceError("USE_CASE_UNKNOWN", lambda: self.plane.subject("UNKNOWN"))

    def test_subject_digest_changes_with_model_revision(self):
        before = self.plane.subject_digest("AI-UC-2500")
        self.plane.models["MODEL-012"]["revision"] = "model-v13"
        self.assertNotEqual(before, self.plane.subject_digest("AI-UC-2500"))

    def test_subject_digest_changes_with_agent_tools(self):
        before = self.plane.subject_digest("AI-UC-2500")
        self.plane.agents["AGENT-2500"]["tool_ids"].append("TOOL-UNDERWRITING-MUTATE")
        self.assertNotEqual(before, self.plane.subject_digest("AI-UC-2500"))

    def test_risk_score_selects_consequential_tier(self):
        decision = self.plane.evaluate("AI-UC-2500", LATER)
        self.assertEqual(decision.risk_tier, "CONSEQUENTIAL")

    def test_risk_downgrade_is_blocked(self):
        self.plane.use_cases["AI-UC-2500"]["risk_tier"] = "LOW"
        self.assertIn("RISK_TIER_MISMATCH", self.plane.evaluate("AI-UC-2500", LATER).findings)

    def test_authoritative_tool_sets_mandatory_floor(self):
        self.plane.assessments["AI-UC-2500"]["dimensions"] = {"decision_consequence": 1}
        self.plane.use_cases["AI-UC-2500"]["risk_tier"] = "CONSEQUENTIAL"
        self.plane.agents["AGENT-2500"]["tool_ids"].append("TOOL-UNDERWRITING-MUTATE")
        decision = self.plane.evaluate("AI-UC-2500", LATER)
        self.assertEqual(decision.risk_tier, "CONSEQUENTIAL")
        self.assertIn("UNAUTHORIZED_AUTONOMY", decision.findings)

    def test_registration_is_not_approval(self):
        self.plane.use_cases["AI-UC-2500"]["lifecycle"] = "REGISTERED"
        self.assertIn("USE_CASE_NOT_APPROVED", self.plane.evaluate("AI-UC-2500", LATER).findings)

    def test_revoked_model_is_blocked(self):
        self.plane.models["MODEL-012"]["status"] = "REVOKED"
        self.assertIn("MODEL_NOT_APPROVED", self.plane.evaluate("AI-UC-2500", LATER).findings)

    def test_model_task_mismatch_is_blocked(self):
        self.plane.models["MODEL-012"]["permitted_tasks"] = ["ADVISORY_SUMMARY"]
        self.assertIn("MODEL_TASK_NOT_PERMITTED", self.plane.evaluate("AI-UC-2500", LATER).findings)

    def test_unknown_data_residency_is_insufficient_evidence(self):
        self.plane.use_cases["AI-UC-2500"]["data_residency"] = "UNKNOWN"
        decision = self.plane.evaluate("AI-UC-2500", LATER)
        self.assertEqual(decision.decision, "INSUFFICIENT_EVIDENCE")
        self.assertIn("DATA_RESIDENCY_UNKNOWN", decision.findings)

    def test_missing_human_oversight_blocks_consequential_use(self):
        self.plane.use_cases["AI-UC-2500"]["human_oversight"] = "UNVERIFIED"
        self.assertIn("HUMAN_OVERSIGHT_UNVERIFIED", self.plane.evaluate("AI-UC-2500", LATER).findings)

    def test_missing_required_evidence_is_not_allowed(self):
        register_required(self.plane, omit={"privacy"})
        decision = self.plane.evaluate("AI-UC-2500", LATER)
        self.assertEqual(decision.decision, "INSUFFICIENT_EVIDENCE")
        self.assertIn("EVIDENCE_MISSING:privacy", decision.findings)

    def test_forged_evidence_is_rejected(self):
        record, _ = evidence_for(self.plane, "security")
        self.assertGovernanceError(
            "EVIDENCE_AUTHENTICITY_UNVERIFIED",
            lambda: self.plane.register_evidence("AI-UC-2500", record, "hmac-sha256:fake", NOW),
        )

    def test_future_evidence_is_rejected(self):
        record, _ = evidence_for(self.plane, "security")
        future = Evidence(**{**record.payload(), "issued_at": FUTURE})
        key = self.plane.keys["security-verification-v1"]
        signature = sign_evidence(future, key)
        self.assertGovernanceError(
            "EVIDENCE_FROM_FUTURE",
            lambda: self.plane.register_evidence("AI-UC-2500", future, signature, NOW),
        )

    def test_untrusted_evidence_producer_is_rejected(self):
        record, _ = evidence_for(self.plane, "security")
        forged = Evidence(**{**record.payload(), "producer": "coding-agent-2500"})
        self.assertGovernanceError(
            "EVIDENCE_PRODUCER_UNTRUSTED",
            lambda: self.plane.register_evidence("AI-UC-2500", forged, "anything", NOW),
        )

    def test_wrong_subject_evidence_is_rejected(self):
        record, _ = evidence_for(self.plane, "security")
        wrong = Evidence(**{**record.payload(), "subject_digest": "sha256:other"})
        key = self.plane.keys["security-verification-v1"]
        signature = sign_evidence(wrong, key)
        self.assertGovernanceError(
            "EVIDENCE_SUBJECT_MISMATCH",
            lambda: self.plane.register_evidence("AI-UC-2500", wrong, signature, NOW),
        )

    def test_expired_evidence_is_insufficient(self):
        for kind in self.plane.policy["required_evidence"]["CONSEQUENTIAL"]:
            record, _ = evidence_for(self.plane, kind, expires_at=NOW)
            key_id = self.plane.trust["evidence_producers"][record.producer]["key_id"]
            self.plane.register_evidence(
                "AI-UC-2500", record, sign_evidence(record, self.plane.keys[key_id]), NOW
            )
        decision = self.plane.evaluate("AI-UC-2500", LATER)
        self.assertEqual(decision.decision, "INSUFFICIENT_EVIDENCE")
        self.assertTrue(any(item.startswith("EVIDENCE_EXPIRED") for item in decision.findings))

    def test_model_change_invalidates_registered_evidence(self):
        register_required(self.plane)
        self.plane.models["MODEL-012"]["revision"] = "model-v13"
        decision = self.plane.evaluate("AI-UC-2500", LATER)
        self.assertEqual(decision.decision, "INSUFFICIENT_EVIDENCE")
        self.assertTrue(any("STALE_SUBJECT" in item for item in decision.findings))

    def test_complete_current_evidence_is_eligible_not_automatically_allowed(self):
        decision = self.eligible()
        self.assertEqual(decision.decision, "ELIGIBLE_FOR_ACCOUNTABLE_APPROVAL")

    def test_agent_cannot_self_approve(self):
        decision = self.eligible()
        self.assertGovernanceError(
            "APPROVER_NOT_AUTHORIZED",
            lambda: self.plane.approve(
                "AI-UC-2500", decision.subject_digest, "SESSION-AGENT",
                "operate_bounded_use_case", LATER, FUTURE,
            ),
        )

    def test_approval_is_exact_subject_bound(self):
        self.eligible()
        self.assertGovernanceError(
            "APPROVAL_SUBJECT_MISMATCH",
            lambda: self.plane.approve(
                "AI-UC-2500", "sha256:other", "SESSION-AI-GOV",
                "operate_bounded_use_case", LATER, FUTURE,
            ),
        )

    def test_approval_is_exact_action_bound(self):
        decision = self.eligible()
        self.assertGovernanceError(
            "APPROVAL_ACTION_OUT_OF_SCOPE",
            lambda: self.plane.approve(
                "AI-UC-2500", decision.subject_digest, "SESSION-AI-GOV",
                "deploy_any_system", LATER, FUTURE,
            ),
        )

    def test_only_protected_executor_can_consume_approval(self):
        receipt = self.receipt()
        self.assertGovernanceError(
            "EXECUTOR_NOT_AUTHORIZED",
            lambda: self.plane.authorize_operation(receipt.receipt_id, "OP-1", "SESSION-AGENT", LATER),
        )

    def test_unknown_session_does_not_create_identity(self):
        self.assertGovernanceError(
            "UNAUTHENTICATED_PRINCIPAL",
            lambda: self.plane.authenticate("SESSION-CLAIMED-ADMIN"),
        )

    def test_valid_approval_allows_exact_operation(self):
        receipt = self.receipt()
        decision = self.plane.authorize_operation(receipt.receipt_id, "OP-1", "SESSION-EXECUTOR", LATER)
        self.assertEqual(decision.decision, "ALLOWED")

    def test_expired_approval_is_rejected(self):
        decision = self.eligible()
        receipt = self.plane.approve(
            "AI-UC-2500", decision.subject_digest, "SESSION-AI-GOV",
            "operate_bounded_use_case", NOW, LATER,
        )
        self.assertGovernanceError(
            "APPROVAL_EXPIRED",
            lambda: self.plane.authorize_operation(receipt.receipt_id, "OP-LATE", "SESSION-EXECUTOR", FUTURE),
        )

    def test_approval_is_single_use(self):
        receipt = self.receipt()
        self.plane.authorize_operation(receipt.receipt_id, "OP-1", "SESSION-EXECUTOR", LATER)
        self.assertGovernanceError(
            "APPROVAL_ALREADY_CONSUMED",
            lambda: self.plane.authorize_operation(receipt.receipt_id, "OP-2", "SESSION-EXECUTOR", LATER),
        )

    def test_concurrent_consumption_allows_one_operation(self):
        receipt = self.receipt()

        def consume(number):
            try:
                return self.plane.authorize_operation(
                    receipt.receipt_id, f"OP-{number}", "SESSION-EXECUTOR", LATER
                ).decision
            except GovernanceError as exc:
                return exc.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(consume, (1, 2)))
        self.assertEqual(results.count("ALLOWED"), 1)
        self.assertEqual(results.count("APPROVAL_ALREADY_CONSUMED"), 1)

    def test_policy_change_invalidates_approval(self):
        receipt = self.receipt()
        self.plane.policy["version"] = "ENTERPRISE-AI-POLICY@5"
        self.assertGovernanceError(
            "APPROVAL_POLICY_STALE",
            lambda: self.plane.authorize_operation(receipt.receipt_id, "OP-1", "SESSION-EXECUTOR", LATER),
        )

    def test_model_change_invalidates_approval_at_point_of_use(self):
        receipt = self.receipt()
        self.plane.models["MODEL-012"]["revision"] = "model-v13"
        self.assertGovernanceError(
            "APPROVAL_SUBJECT_STALE",
            lambda: self.plane.authorize_operation(receipt.receipt_id, "OP-1", "SESSION-EXECUTOR", LATER),
        )

    def test_approver_authority_is_rechecked(self):
        receipt = self.receipt()
        self.plane.principals["ai-governance-owner-1"]["status"] = "REVOKED"
        self.assertGovernanceError(
            "APPROVAL_AUTHORITY_REVOKED",
            lambda: self.plane.authorize_operation(receipt.receipt_id, "OP-1", "SESSION-EXECUTOR", LATER),
        )

    def test_model_revision_maps_to_targeted_reassessment(self):
        impact = self.plane.change_impact("AI-UC-2500", {"model_revision": "model-v13"})
        self.assertEqual(impact["state"], "REASSESSMENT_REQUIRED")
        self.assertIn("classification_accuracy", impact["required_reassessment"])

    def test_tool_expansion_maps_to_authorization_reassessment(self):
        impact = self.plane.change_impact("AI-UC-2500", {"agent_tools": "expanded"})
        self.assertIn("authorization", impact["required_reassessment"])
        self.assertIn("human_oversight", impact["required_reassessment"])

    def test_authenticated_runtime_violation_suspends_capability(self):
        observation, signature = runtime_violation_for(self.plane)
        decision = self.plane.suspend_on_violation("AI-UC-2500", observation, signature, LATER)
        self.assertEqual(decision.decision, "SUSPENDED")
        self.assertEqual(self.plane.use_cases["AI-UC-2500"]["lifecycle"], "SUSPENDED")
        self.assertIn("HUMAN_REVIEW_BYPASS", decision.findings[0])

    def test_forged_runtime_violation_cannot_suspend_capability(self):
        observation, _ = runtime_violation_for(self.plane)
        self.assertGovernanceError(
            "RUNTIME_VIOLATION_AUTHENTICITY_UNVERIFIED",
            lambda: self.plane.suspend_on_violation(
                "AI-UC-2500", observation, "hmac-sha256:fake", LATER
            ),
        )
        self.assertEqual(
            self.plane.use_cases["AI-UC-2500"]["lifecycle"],
            "APPROVED_FOR_BOUNDED_USE",
        )

    def test_unrelated_metadata_change_does_not_invent_obligations(self):
        impact = self.plane.change_impact("AI-UC-2500", {"display_name": "new label"})
        self.assertEqual(impact["state"], "NO_GOVERNANCE_IMPACT_IDENTIFIED")

    def test_golden_scenarios_execute_all_controls(self):
        report = run_golden_scenarios(SCENARIO)
        self.assertEqual((report["passed"], report["total"]), (13, 13))

    def test_adversarial_evaluations_retain_labelled_population(self):
        report = run_adversarial_evaluations(SCENARIO)
        self.assertEqual((report["passed"], report["total"]), (13, 13))

    def test_reference_stops_at_accountable_review(self):
        report = run_reference(SCENARIO)
        self.assertEqual(report["decision"], "ELIGIBLE_FOR_ACCOUNTABLE_REVIEW")
        self.assertEqual(report["reference"]["operation"]["decision"], "ALLOWED")
        self.assertGreaterEqual(len(report["non_authorities"]), 4)

    def test_rego_excerpt_does_not_contain_fixture_keys(self):
        policy = (SCENARIO / "policies/governance.rego").read_text()
        trust = (SCENARIO / "policies/trust-policy.json").read_text()
        self.assertNotIn("course25-", policy + trust)

    def test_registry_fixtures_are_valid_json(self):
        for path in list((SCENARIO / "registry").glob("*.json")) + list((SCENARIO / "policies").glob("*.json")):
            json.loads(path.read_text())


if __name__ == "__main__":
    unittest.main()
