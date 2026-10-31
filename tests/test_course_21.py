"""Focused verification for Course 21 multi-repository parallel-agent delivery."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from datetime import timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum/intermediate/11-multi-repository-parallel-agent-delivery"
SCENARIO = LESSON / "northstar-parallel-agents"
sys.path.insert(0, str(SCENARIO))
SPEC = importlib.util.spec_from_file_location("course21_lab", SCENARIO / "lab.py")
lab = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)

from parallel_app.control_plane import OperationState, WorkState  # noqa: E402
from parallel_app.git_harness import TrustedGitHarness  # noqa: E402
from parallel_app.simulation import (  # noqa: E402
    NOW,
    complete_unit,
    evaluation_checks,
    golden_scenarios,
    load_json,
    make_plane,
    run_reference,
    scheduling_comparison,
    trusted_revisions,
)


class Course21Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.revisions = trusted_revisions(SCENARIO)

    def fresh(self):
        return make_plane(SCENARIO, self.revisions)

    def test_real_git_harness_builds_five_exact_revision_pairs(self):
        self.assertEqual(len(self.revisions), 5)
        for revision in self.revisions.values():
            self.assertEqual(len(revision.baseline_commit), 40)
            self.assertEqual(len(revision.candidate_commit), 40)
            self.assertTrue(revision.tests_passed)

    def test_actual_git_diff_is_derived_for_every_repository(self):
        for revision in self.revisions.values():
            self.assertEqual(
                set(revision.changed_paths),
                {"spec/work-unit.json", "src/component.py", "tests/test_component.py"},
            )

    def test_contract_is_verified_before_parallel_dispatch(self):
        plane = self.fresh()
        self.assertEqual(plane.work_units["WU-CONTRACT"].state, WorkState.VERIFIED)
        self.assertEqual(set(plane.ready_units()), {"WU-DOC", "WU-AI", "WU-REVIEW"})

    def test_api_and_ui_wait_for_dependencies(self):
        plane = self.fresh()
        self.assertEqual(plane.work_units["WU-API"].state, WorkState.BLOCKED)
        self.assertEqual(plane.work_units["WU-UI"].state, WorkState.BLOCKED)

    def test_two_workers_cannot_hold_the_same_work_unit(self):
        self.assertTrue(golden_scenarios(SCENARIO)["PAR-GOLDEN-001"])

    def test_stale_fencing_generation_cannot_submit(self):
        self.assertTrue(golden_scenarios(SCENARIO)["PAR-GOLDEN-002"])

    def test_unauthorized_path_modification_is_rejected(self):
        self.assertTrue(golden_scenarios(SCENARIO)["PAR-GOLDEN-004"])

    def test_workload_identity_is_authenticated_not_claimed(self):
        checks = evaluation_checks(SCENARIO)
        self.assertTrue(checks["EVAL-016-unauthenticated-worker-denied"])
        self.assertTrue(checks["EVAL-017-wrong-repository-denied"])

    def test_unresolved_contract_stale_and_symbolic_commits_are_rejected(self):
        checks = evaluation_checks(SCENARIO)
        self.assertTrue(checks["EVAL-018-unresolved-candidate-denied"])
        self.assertTrue(checks["EVAL-019-stale-contract-denied"])
        self.assertTrue(checks["EVAL-020-symbolic-revision-denied"])

    def test_agent_completion_does_not_imply_verification(self):
        self.assertTrue(golden_scenarios(SCENARIO)["PAR-GOLDEN-008"])

    def test_evidence_requires_trusted_producer_and_exact_subject(self):
        checks = evaluation_checks(SCENARIO)
        self.assertTrue(checks["EVAL-021-untrusted-verifier-denied"])
        self.assertTrue(checks["EVAL-022-evidence-is-executed-and-bound"])

    def test_submission_uses_trusted_git_diff_not_worker_metadata(self):
        revisions = TrustedGitHarness(SCENARIO).observe(
            extra_files={"ai-service": {"infra/production-admin.tf": "forbidden = true\n"}}
        )
        plane = make_plane(SCENARIO, revisions)
        lease = plane.acquire_lease("WU-AI", authenticated_identity="agent-ai-a", now=NOW)
        plane.start(lease, authenticated_identity="agent-ai-a", now=NOW)
        with self.assertRaisesRegex(PermissionError, "UNAUTHORIZED_PATH_MODIFICATION"):
            plane.submit(
                lease,
                authenticated_identity="agent-ai-a",
                now=NOW + timedelta(minutes=1),
                candidate_commit=revisions["ai-service"].candidate_commit,
                contract_revision=2,
            )

    def test_idempotent_effect_requires_current_lease_and_same_subject(self):
        plane = self.fresh()
        first = plane.acquire_lease("WU-AI", authenticated_identity="agent-ai-a", now=NOW)
        plane.start(first, authenticated_identity="agent-ai-a", now=NOW)
        request = {"action": "CREATE_OR_UPDATE_PR", "repository": "ai-service"}
        plane.execute_idempotent(
            first,
            now=NOW + timedelta(seconds=1),
            operation_id="OP-SUBJECT",
            authenticated_identity="agent-ai-a",
            request=request,
            effect=lambda: {"pull_request": 1},
        )
        plane.fail_and_retry(
            first,
            authenticated_identity="agent-ai-a",
            now=NOW + timedelta(seconds=2),
            reason="TRANSIENT_FAILURE",
        )
        replacement = plane.acquire_lease(
            "WU-AI",
            authenticated_identity="agent-ai-b",
            now=NOW + timedelta(seconds=3),
        )
        plane.start(
            replacement,
            authenticated_identity="agent-ai-b",
            now=NOW + timedelta(seconds=3),
        )
        with self.assertRaisesRegex(PermissionError, "IDEMPOTENCY_SUBJECT_MISMATCH"):
            plane.execute_idempotent(
                replacement,
                now=NOW + timedelta(seconds=4),
                operation_id="OP-SUBJECT",
                authenticated_identity="agent-ai-b",
                request=request,
                effect=lambda: {"pull_request": 2},
            )

    def test_contract_change_revokes_lease_operation_and_fencing_generation(self):
        plane = self.fresh()
        lease = plane.acquire_lease("WU-AI", authenticated_identity="agent-ai-a", now=NOW)
        plane.start(lease, authenticated_identity="agent-ai-a", now=NOW)
        plane.execute_idempotent(
            lease,
            now=NOW + timedelta(seconds=1),
            operation_id="OP-REVOKE",
            authenticated_identity="agent-ai-a",
            request={"action": "CREATE_OR_UPDATE_PR"},
            effect=lambda: {"pull_request": 1},
        )
        contract_v3 = load_json(SCENARIO / "contracts/classification-v3.schema.json")
        proposal = plane.propose_contract_change(
            authenticated_identity="agent-ai-a",
            proposed_revision=3,
            proposed_contract=contract_v3,
            affected_hint=("WU-AI",),
        )
        plane.approve_contract_change(
            proposal,
            authenticated_identity="northstar-contract-owner",
            direct_dependents=("WU-AI",),
        )
        self.assertNotIn("WU-AI", plane.leases)
        self.assertGreater(plane.work_units["WU-AI"].generation, lease.generation)
        self.assertEqual(plane.operations["OP-REVOKE"].state, OperationState.REVOKED)

    def test_cross_service_scenarios_execute_protected_behaviors(self):
        results = self.revisions.system_results
        self.assertEqual(
            set(results),
            {
                "ambiguity_routes_to_review",
                "tenant_isolation",
                "duplicate_operation_reconciled",
                "expired_approval_rejected",
                "proposal_not_authoritative",
                "provenance_preserved",
            },
        )
        self.assertTrue(all(results.values()))

    def test_duplicate_pr_operation_has_one_effect(self):
        self.assertTrue(golden_scenarios(SCENARIO)["PAR-GOLDEN-006"])

    def test_idempotency_key_cannot_be_reused_for_different_request(self):
        self.assertTrue(evaluation_checks(SCENARIO)["EVAL-023-idempotency-key-conflict-denied"])

    def test_checkpoint_cannot_resume_against_stale_repository(self):
        self.assertTrue(golden_scenarios(SCENARIO)["PAR-GOLDEN-007"])

    def test_contract_change_requires_owner_and_selective_invalidation(self):
        self.assertTrue(golden_scenarios(SCENARIO)["PAR-GOLDEN-005"])

    def test_unaffected_document_work_is_preserved_on_contract_change(self):
        plane = self.fresh()
        contract_v3 = load_json(SCENARIO / "contracts/classification-v3.schema.json")
        proposal = plane.propose_contract_change(
            authenticated_identity="agent-ai-a",
            proposed_revision=3,
            proposed_contract=contract_v3,
            affected_hint=("WU-AI", "WU-REVIEW"),
        )
        affected = plane.approve_contract_change(
            proposal,
            authenticated_identity="northstar-contract-owner",
            direct_dependents=("WU-AI", "WU-REVIEW"),
        )
        self.assertNotIn("WU-DOC", affected)
        self.assertEqual(plane.work_units["WU-DOC"].state, WorkState.READY)

    def test_retry_budget_escalates_instead_of_looping(self):
        self.assertTrue(golden_scenarios(SCENARIO)["PAR-GOLDEN-011"])

    def test_restart_preserves_lease_generation_and_operation_result(self):
        self.assertTrue(golden_scenarios(SCENARIO)["PAR-GOLDEN-012"])

    def test_dependency_progression_releases_api_then_ui(self):
        plane = self.fresh()
        complete_unit(plane, "WU-DOC", self.revisions["document-service"], "agent-document")
        complete_unit(plane, "WU-REVIEW", self.revisions["review-service"], "agent-review")
        self.assertIn("WU-API", plane.ready_units())
        complete_unit(plane, "WU-API", self.revisions["underwriting-api"], "agent-api")
        self.assertIn("WU-UI", plane.ready_units())

    def test_exact_revision_manifest_is_required(self):
        self.assertTrue(golden_scenarios(SCENARIO)["PAR-GOLDEN-009"])

    def test_system_failure_blocks_integration(self):
        self.assertTrue(evaluation_checks(SCENARIO)["EVAL-027-failed-system-scenario-blocks"])

    def test_reference_stops_at_integration_review_eligibility(self):
        _, _, _, results, decision = run_reference(SCENARIO)
        self.assertTrue(all(results.values()))
        self.assertEqual(decision.state, "READY_FOR_INTEGRATION_REVIEW")
        self.assertFalse(decision.merge_authorized)
        self.assertFalse(decision.deployment_authorized)
        self.assertFalse(decision.release_authorized)

    def test_coordinator_cannot_authorize_release(self):
        self.assertTrue(golden_scenarios(SCENARIO)["PAR-GOLDEN-010"])

    def test_scheduling_comparison_uses_elapsed_not_summed_parallel_time(self):
        comparison = scheduling_comparison(SCENARIO)
        self.assertEqual(comparison["sequential"]["elapsed_hours"], 30)
        self.assertEqual(comparison["naive_parallel"]["rework_hours"], 15)
        self.assertEqual(comparison["governed_parallel"]["elapsed_hours"], 20)
        self.assertLess(
            comparison["governed_parallel"]["elapsed_hours"],
            comparison["naive_parallel"]["elapsed_hours"],
        )

    def test_twelve_golden_scenarios_pass(self):
        results = golden_scenarios(SCENARIO)
        self.assertEqual(len(results), 12)
        self.assertTrue(all(results.values()))

    def test_thirty_labelled_evaluation_decisions_pass(self):
        results = evaluation_checks(SCENARIO)
        self.assertEqual(len(results), 30)
        self.assertTrue(all(results.values()))

    def test_report_uses_honest_metric_populations(self):
        report = lab.build_report()
        self.assertEqual(report["evaluation"]["population"], {
            "positive": 7,
            "negative": 15,
            "boundary": 5,
            "failure_recovery": 3,
        })
        self.assertIn("not production benchmarks", report["limitations"][0])

    def test_lab_report_is_complete_and_bounded(self):
        report = lab.build_report()
        self.assertEqual(report["course_validation"]["status"], "PASS")
        self.assertEqual(report["candidate_assessment"]["status"], "READY_FOR_INTEGRATION_REVIEW")
        self.assertEqual((report["conformance"]["passed"], report["conformance"]["total"]), (12, 12))
        self.assertEqual((report["evaluation"]["passed"], report["evaluation"]["total"]), (30, 30))
        self.assertEqual((report["system_scenarios"]["passed"], report["system_scenarios"]["total"]), (6, 6))

    def test_contract_behavior_preserves_prior_course_invariants(self):
        behavior = (SCENARIO / "contracts/classification.behavior.md").read_text()
        self.assertIn("regardless of model confidence", behavior)
        self.assertIn("MUST NOT", behavior)

    def test_course_21_fixture_declares_no_release_authority(self):
        policy = load_json(SCENARIO / "parent-change/integration-policy.json")
        self.assertFalse(policy["release_authority_in_fixture"])


if __name__ == "__main__":
    unittest.main()
