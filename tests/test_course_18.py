"""Focused verification for Course 18 brownfield development."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum" / "intermediate" / "08-brownfield-development-with-agentic-coding-agents"
SCENARIO = LESSON / "northstar-underwriter-modernization"
sys.path.insert(0, str(SCENARIO))

from brownfield_app.contracts import AuthorizationGrant, BehaviorRecord, ExecutionContext, Submission  # noqa: E402
from brownfield_app.discovery import (  # noqa: E402
    required_regression_tests,
    validate_behavior_records,
    validate_discovery_manifest,
)
from brownfield_app.governance import (  # noqa: E402
    EXPECTED_REPOSITORY_REVISION,
    EXPECTED_SPECIFICATION_REVISION,
    POLICY_REVISION,
    PROTECTED_TESTS,
    TrustedAuthorizationRegistry,
    check_v1_semantics,
    compare_shadow_outputs,
    exercise_rollback,
    persist_proposal,
    select_summary_provider,
)
from brownfield_app.legacy import (  # noqa: E402
    AISummaryProvider,
    LegacySummaryProvider,
    classify_risk,
    legacy_v1_response,
)
from brownfield_app.migration import ProposalStore  # noqa: E402
from lab import build_candidate  # noqa: E402
from brownfield_app.governance import evaluate_candidate  # noqa: E402


class Course18Tests(unittest.TestCase):
    def _context(self, actor: str = "underwriter-17") -> ExecutionContext:
        return ExecutionContext(
            EXPECTED_REPOSITORY_REVISION,
            EXPECTED_SPECIFICATION_REVISION,
            actor,
            frozenset({"ai_risk_summary"}),
            frozenset({"create_summary_proposal", "persist_summary_proposal"}),
        )

    def _registry(self, submission_id: str = "SUB-1") -> TrustedAuthorizationRegistry:
        return TrustedAuthorizationRegistry(
            {
                AuthorizationGrant("underwriter-17", submission_id, operation, POLICY_REVISION)
                for operation in ("create_summary_proposal", "persist_summary_proposal")
            }
        )

    def test_characterization_boundaries(self) -> None:
        self.assertEqual([classify_risk(v) for v in (49, 50, 79, 80)], ["LOW", "MEDIUM", "MEDIUM", "HIGH"])

    def test_high_risk_requires_review(self) -> None:
        response = legacy_v1_response(Submission("SUB-1", 80, ("DOC-1",)))
        self.assertEqual(response["risk_category"], "HIGH")
        self.assertIs(response["review_required"], True)

    def test_semantic_break_is_detected(self) -> None:
        submission = Submission("SUB-1", 90, ("DOC-1",))
        candidate = {"submission_id": "SUB-1", "risk_category": "HIGH", "review_required": False}
        decision = check_v1_semantics(submission, candidate)
        self.assertEqual(decision.state, "BLOCKED")

    def test_compatible_optional_v1_field_is_allowed(self) -> None:
        submission = Submission("SUB-1", 90, ("DOC-1",))
        candidate = legacy_v1_response(submission) | {"trace_id": "TRACE-1"}
        decision = check_v1_semantics(submission, candidate)
        self.assertEqual(decision.state, "PASS")

    def test_exact_identity_contract_can_reject_optional_field(self) -> None:
        submission = Submission("SUB-1", 90, ("DOC-1",))
        candidate = legacy_v1_response(submission) | {"trace_id": "TRACE-1"}
        contract = json.loads(
            (SCENARIO / "specs" / "AI-2410" / "v1-compatibility-contract.json").read_text()
        )
        contract["exact_response_identity"] = True
        decision = check_v1_semantics(submission, candidate, contract)
        self.assertIn("V1_EXACT_IDENTITY_BREAK", {item.code for item in decision.findings})

    def test_v1_required_field_type_is_enforced(self) -> None:
        submission = Submission("SUB-1", 90, ("DOC-1",))
        candidate = legacy_v1_response(submission) | {"review_required": "true"}
        decision = check_v1_semantics(submission, candidate)
        self.assertIn("V1_CONTRACT_TYPE_ERROR", {item.code for item in decision.findings})

    def test_ai_proposal_never_authoritative(self) -> None:
        proposal = AISummaryProvider().generate(Submission("SUB-1", 55, ("DOC-1",)))
        self.assertFalse(proposal.authoritative)

    def test_feature_flag_is_not_authorization(self) -> None:
        submission = Submission("SUB-1", 55, ("DOC-1",))
        context = self._context(actor="observer")
        provider, decision = select_summary_provider(context, submission, self._registry())
        self.assertIsNone(provider)
        self.assertEqual(decision.state, "BLOCKED")

    def test_authorization_grant_is_exactly_subject_operation_and_policy_bound(self) -> None:
        registry = self._registry()
        self.assertTrue(
            registry.permits(
                principal="underwriter-17",
                submission_id="SUB-1",
                operation="create_summary_proposal",
                policy_revision=POLICY_REVISION,
            )
        )
        self.assertFalse(
            registry.permits(
                principal="underwriter-17",
                submission_id="SUB-2",
                operation="create_summary_proposal",
                policy_revision=POLICY_REVISION,
            )
        )
        self.assertFalse(
            registry.permits(
                principal="underwriter-17",
                submission_id="SUB-1",
                operation="persist_summary_proposal",
                policy_revision=POLICY_REVISION - 1,
            )
        )

    def test_authorization_is_rechecked_before_persistence(self) -> None:
        submission = Submission("SUB-1", 55, ("DOC-1",))
        proposal = AISummaryProvider().generate(submission)
        status, decision = persist_proposal(
            context=self._context(actor="observer"),
            submission=submission,
            proposal=proposal,
            source_revision="legacy@1",
            registry=self._registry(),
            store=ProposalStore(),
        )
        self.assertIsNone(status)
        self.assertEqual(decision.state, "BLOCKED")

    def test_transactional_retry(self) -> None:
        store = ProposalStore()
        proposal = AISummaryProvider().generate(Submission("SUB-1", 55, ("DOC-1",)))
        self.assertEqual(store.migrate(proposal, "legacy@1"), "APPLIED")
        self.assertEqual(store.migrate(proposal, "legacy@1"), "ALREADY_APPLIED")
        self.assertEqual(store.count(), 1)
        self.assertEqual(store.authoritative_count(), 0)

    def test_conflicting_retry_is_rejected(self) -> None:
        store = ProposalStore()
        proposal = AISummaryProvider().generate(Submission("SUB-1", 55, ("DOC-1",)))
        conflicting = type(proposal)(
            proposal.submission_id,
            proposal.source,
            proposal.text + " changed",
            proposal.evidence,
            proposal.authoritative,
        )
        self.assertEqual(store.migrate(proposal, "legacy@1"), "APPLIED")
        self.assertEqual(store.migrate(conflicting, "legacy@1"), "IDEMPOTENCY_CONFLICT")
        self.assertEqual(store.count(), 1)

    def test_unknown_behavior_blocks_retirement(self) -> None:
        result = validate_behavior_records([BehaviorRecord("BEH-1", "UNKNOWN", None, ("TRACE-1",))])
        self.assertEqual(result.state, "BLOCKED")
        self.assertIn("UNKNOWN_BEHAVIOR", {item.code for item in result.findings})

    def test_selective_regression_keeps_protected_invariants(self) -> None:
        plan = required_regression_tests(
            impacted_consumers={"SubmissionAPIv1"},
            mapped_tests={"CHANGED_COMPONENT": {"test_provider"}, "SubmissionAPIv1": {"test_v1"}},
            protected_tests=PROTECTED_TESTS,
        )
        self.assertTrue(PROTECTED_TESTS.issubset(plan.selected_tests))
        self.assertEqual(plan.state, "PASS")

    def test_unmapped_critical_consumer_blocks_regression_plan(self) -> None:
        plan = required_regression_tests(
            impacted_consumers={"SubmissionAPIv1", "LegacyPortal"},
            mapped_tests={"SubmissionAPIv1": {"test_v1"}},
            protected_tests=PROTECTED_TESTS,
            critical_consumers={"SubmissionAPIv1", "LegacyPortal"},
        )
        self.assertEqual(plan.state, "BLOCKED")
        self.assertEqual(plan.unmapped_consumers, frozenset({"LegacyPortal"}))

    def test_discovery_omission_is_detected_from_independent_evidence(self) -> None:
        manifest = json.loads((SCENARIO / "fixtures" / "discovery-manifest.json").read_text())
        evidence = json.loads((SCENARIO / "fixtures" / "trusted-dependency-evidence.json").read_text())
        manifest["findings"][0]["consumers"].remove("NightlyRiskBatch")
        decision = validate_discovery_manifest(
            manifest,
            actual_repository_revision=EXPECTED_REPOSITORY_REVISION,
            trusted_dependency_evidence=evidence,
        )
        self.assertIn("INCOMPLETE_IMPACT_GRAPH", {item.code for item in decision.findings})

    def test_shadow_divergence_is_measured_from_outputs(self) -> None:
        submission = Submission("SUB-1", 55, ("DOC-1",))
        legacy = LegacySummaryProvider().generate(submission)
        candidate = AISummaryProvider().generate(submission)
        expected = compare_shadow_outputs(legacy, candidate, approved_differences={"source", "text"})
        unsafe = compare_shadow_outputs(
            legacy,
            type(candidate)("SUB-WRONG", candidate.source, candidate.text, candidate.evidence, False),
            approved_differences={"source", "text"},
        )
        self.assertEqual(expected.classification, "EXPECTED")
        self.assertEqual(unsafe.classification, "UNEXPECTED")

    def test_stale_repository_blocks(self) -> None:
        decision = evaluate_candidate(build_candidate(["stale_repository"]))
        self.assertEqual(decision.state, "BLOCKED")

    def test_rollback_rehearsal_restores_legacy_path(self) -> None:
        submission = Submission("SUB-1", 55, ("DOC-1",))
        evidence = exercise_rollback(
            submission=submission,
            context=self._context(),
            registry=self._registry(),
            store=ProposalStore(),
            source_revision="rollback@1",
        )
        self.assertTrue(evidence.passed)

    def test_evaluator_uses_artifact_behavior_not_failure_labels(self) -> None:
        candidate = build_candidate()
        candidate["semantic_break"] = True
        self.assertEqual(evaluate_candidate(candidate).state, "PASS")
        candidate["candidate_v1_response"]["review_required"] = False
        self.assertEqual(evaluate_candidate(candidate).state, "BLOCKED")

    def test_reference_package_cannot_authorize_release(self) -> None:
        package = json.loads((SCENARIO / "reference" / "modernization-package.json").read_text())
        self.assertFalse(package["merge_authorized"])
        self.assertFalse(package["deployment_authorized"])
        self.assertFalse(package["legacy_retirement_authorized"])

    def test_delta_has_no_retirements(self) -> None:
        delta = json.loads((SCENARIO / "specs" / "AI-2410" / "semantic-delta.yaml").read_text())
        self.assertEqual(delta["retired"], [])
        self.assertIn("REQ-RISK-010", {item["requirement_id"] for item in delta["preserved"]})

    def test_impact_graph_keeps_investigation_blocker(self) -> None:
        impact = json.loads((SCENARIO / "specs" / "AI-2410" / "impact-analysis.json").read_text())
        portal = next(item for item in impact["consumers"] if item["id"] == "LegacyPortal")
        self.assertEqual(portal["impact"], "INVESTIGATE")
        self.assertTrue(portal["block_retirement"])

    def test_starter_has_five_decisions(self) -> None:
        starter = (SCENARIO / "workshop" / "starter" / "modernization-package.json").read_text()
        self.assertEqual(starter.count("TODO-"), 5)

    def test_lab_report(self) -> None:
        result = subprocess.run([sys.executable, str(SCENARIO / "lab.py")], cwd=ROOT, text=True, capture_output=True, check=True)
        report = json.loads(result.stdout)
        self.assertEqual(report["conformance"]["passed"], 12)
        self.assertEqual(report["evaluation"]["passed"], 24)
        self.assertEqual(report["experiments"]["passed"], 10)
        self.assertEqual(report["reference"]["state"], "READY_FOR_INTEGRATION_REVIEW")


if __name__ == "__main__":
    unittest.main()
