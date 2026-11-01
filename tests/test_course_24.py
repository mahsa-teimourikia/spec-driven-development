"""Focused verification for Course 24 release governance."""
from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum/intermediate/14-ci-cd-quality-gates-evidence-based-release-governance"
SCENARIO = LESSON / "northstar-release-control"
sys.path.insert(0, str(SCENARIO))

from release_app.builder import deterministic_build, file_digest  # noqa: E402
from release_app.control_plane import RELEASE_STATES, ReleaseControlPlane  # noqa: E402
from release_app.models import Evidence, ReleaseError  # noqa: E402
from release_app.simulation import (  # noqa: E402
    FUTURE, LATER, NOW, _approve, _dependencies, _safe_observations, prepare_candidate,
    run_adversarial_evaluations, run_golden_scenarios, run_reference, valid_release,
)


class Course24Tests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="course24-test-")

    def tearDown(self):
        self.directory.cleanup()

    def assertReleaseError(self, code, operation):
        with self.assertRaises(ReleaseError) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def candidate(self, **options):
        return prepare_candidate(SCENARIO, self.directory.name, **options)

    def test_manifest_digest_changes_with_model(self):
        _, manifest, _ = self.candidate()
        self.assertNotEqual(manifest.digest, replace(manifest, model_revision="model-v13").digest)

    def test_manifest_digest_changes_with_prompt(self):
        _, manifest, _ = self.candidate()
        self.assertNotEqual(manifest.digest, replace(manifest, prompt_digest="sha256:prompt-v8").digest)

    def test_deterministic_build_repeats_exact_digest(self):
        first = Path(self.directory.name) / "first.bin"
        second = Path(self.directory.name) / "second.bin"
        source = SCENARIO / "source/classifier.py"
        self.assertEqual(deterministic_build(source, first, "abc"), deterministic_build(source, second, "abc"))

    def test_artifact_byte_change_changes_digest(self):
        _, _, artifact = self.candidate()
        before = file_digest(artifact)
        artifact.write_bytes(artifact.read_bytes() + b"changed")
        self.assertNotEqual(before, file_digest(artifact))

    def test_untrusted_builder_is_rejected(self):
        self.assertReleaseError("PROVENANCE_IDENTITY_UNTRUSTED", lambda: self.candidate(builder_id="coding-agent"))

    def test_unapproved_source_branch_is_rejected(self):
        self.assertReleaseError("PROVENANCE_SOURCE_UNAPPROVED", lambda: self.candidate(source_branch="refs/heads/agent-temp"))

    def test_exact_candidate_is_eligible_not_automatically_deployed(self):
        plane, manifest, artifact = self.candidate()
        decision = plane.evaluate(manifest, artifact, LATER)
        self.assertEqual(decision.state, "ELIGIBLE_FOR_RELEASE_REVIEW")
        self.assertIsNone(plane.environment_state()["release_id"])

    def test_modified_artifact_is_blocked_at_gate(self):
        plane, manifest, artifact = self.candidate()
        artifact.write_bytes(artifact.read_bytes() + b"tampered")
        self.assertIn("ARTIFACT_MISMATCH", plane.evaluate(manifest, artifact, LATER).reason_codes)

    def test_missing_sbom_is_blocking(self):
        plane, manifest, artifact = self.candidate(missing=frozenset({"sbom"}))
        self.assertIn("MISSING_EVIDENCE:sbom", plane.evaluate(manifest, artifact, LATER).reason_codes)

    def test_failed_dependency_evidence_is_blocking(self):
        plane, manifest, artifact = self.candidate(prohibited_dependency=True)
        self.assertIn("EVIDENCE_FAILED:sbom", plane.evaluate(manifest, artifact, LATER).reason_codes)

    def test_model_change_invalidates_ai_evaluation(self):
        plane, manifest, artifact = self.candidate(
            manifest_changes={"model_revision": "model-v13"},
            dependency_overrides={"ai_evaluation": {"model_revision": "model-v12"}},
        )
        self.assertIn("STALE_EVIDENCE:ai_evaluation", plane.evaluate(manifest, artifact, LATER).reason_codes)

    def test_prompt_change_invalidates_ai_evaluation(self):
        plane, manifest, artifact = self.candidate(
            manifest_changes={"prompt_digest": "sha256:prompt-v8"},
            dependency_overrides={"ai_evaluation": {"prompt_digest": "sha256:prompt-v7"}},
        )
        self.assertIn("STALE_EVIDENCE:ai_evaluation", plane.evaluate(manifest, artifact, LATER).reason_codes)

    def test_retrieval_change_invalidates_ai_evaluation(self):
        plane, manifest, artifact = self.candidate(
            manifest_changes={"retrieval_revision": "index-2026-10-31"},
            dependency_overrides={"ai_evaluation": {"retrieval_revision": "index-2026-10-30"}},
        )
        self.assertIn("STALE_EVIDENCE:ai_evaluation", plane.evaluate(manifest, artifact, LATER).reason_codes)

    def test_dataset_change_invalidates_ai_evaluation(self):
        plane, manifest, artifact = self.candidate(
            manifest_changes={"dataset_digest": "sha256:dataset-v5"},
            dependency_overrides={"ai_evaluation": {"dataset_digest": "sha256:dataset-underwriting-eval-v4"}},
        )
        self.assertIn("STALE_EVIDENCE:ai_evaluation", plane.evaluate(manifest, artifact, LATER).reason_codes)

    def test_unapproved_tool_policy_is_blocking(self):
        plane, manifest, artifact = self.candidate(manifest_changes={"tool_policy_revision": "TOOL-POLICY@10"})
        self.assertIn("TOOL_POLICY_UNAPPROVED", plane.evaluate(manifest, artifact, LATER).reason_codes)

    def test_agent_self_report_is_not_evidence(self):
        plane, manifest, _ = self.candidate()
        fake = Evidence("EVD-FAKE", "security", manifest.digest, "northstar-security-runner", "PASS", _dependencies(manifest, "security"), {})
        self.assertReleaseError("EVIDENCE_AUTHENTICITY_UNVERIFIED", lambda: plane.register_evidence(manifest.release_id, fake, "hmac-sha256:agent-claim", NOW))

    def test_unknown_session_is_not_identity(self):
        plane, _, _ = self.candidate()
        self.assertReleaseError("UNAUTHENTICATED_PRINCIPAL", lambda: plane.authenticate("release-manager"))

    def test_wrong_role_does_not_create_authority(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        self.assertReleaseError("APPROVER_NOT_AUTHORIZED", lambda: plane.approve(manifest.release_id, manifest.digest, "production", "SESSION-RELEASE", "ai_governance_owner", NOW, FUTURE))

    def test_approval_is_manifest_bound(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        self.assertReleaseError("APPROVAL_SUBJECT_MISMATCH", lambda: plane.approve(manifest.release_id, "sha256:other", "production", "SESSION-RELEASE", "release_authority", NOW, FUTURE))

    def test_one_approval_cannot_satisfy_dual_control(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        receipt = plane.approve(manifest.release_id, manifest.digest, "production", "SESSION-RELEASE", "release_authority", NOW, FUTURE)
        self.assertReleaseError("REQUIRED_APPROVAL_MISSING", lambda: plane.deploy(manifest, (receipt,), "OP-ONE", LATER))

    def test_expired_approval_is_rejected(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        release = plane.approve(manifest.release_id, manifest.digest, "production", "SESSION-RELEASE", "release_authority", "2026-10-31T15:00:00Z", NOW)
        governance = plane.approve(manifest.release_id, manifest.digest, "production", "SESSION-AI-GOV", "ai_governance_owner", "2026-10-31T15:00:00Z", NOW)
        self.assertReleaseError("APPROVAL_EXPIRED_OR_REVOKED", lambda: plane.deploy(manifest, (release, governance), "OP-EXPIRED", LATER))

    def test_valid_deployment_records_state_machine(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        decision = plane.deploy(manifest, _approve(plane, manifest), "OP-VALID", LATER)
        self.assertEqual(decision.state, "VERIFYING")
        self.assertEqual([row["state"] for row in plane.operation_events("OP-VALID")], ["AUTHORIZED", "DISPATCHED", "VERIFYING"])

    def test_deployed_artifact_is_exact_verified_digest(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        plane.deploy(manifest, _approve(plane, manifest), "OP-VALID", LATER)
        self.assertEqual(plane.environment_state()["manifest"]["artifact_digest"], manifest.artifact_digest)

    def test_approval_receipts_are_single_use(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        receipts = _approve(plane, manifest)
        plane.deploy(manifest, receipts, "OP-ONCE", LATER)
        self.assertReleaseError("RELEASE_NOT_ELIGIBLE", lambda: plane.deploy(manifest, receipts, "OP-TWICE", LATER))

    def test_concurrent_deployment_accepts_exactly_one_operation(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        receipts = _approve(plane, manifest)
        barrier = threading.Barrier(2)

        def attempt(operation_id):
            barrier.wait()
            try:
                return plane.deploy(manifest, receipts, operation_id, LATER).state
            except ReleaseError as exc:
                return exc.code

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = sorted(executor.map(attempt, ("OP-RACE-A", "OP-RACE-B")))
        self.assertEqual(outcomes, ["RELEASE_NOT_ELIGIBLE", "VERIFYING"])
        self.assertEqual(plane.operation_count(manifest.release_id), 1)

    def test_safe_runtime_evidence_activates_release(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        plane.deploy(manifest, _approve(plane, manifest), "OP-ACTIVE", LATER)
        self.assertEqual(plane.verify_runtime("OP-ACTIVE", _safe_observations(), LATER).state, "ACTIVE")

    def test_ambiguous_review_bypass_halts_release(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        plane.deploy(manifest, _approve(plane, manifest), "OP-HALT", LATER)
        result = plane.verify_runtime("OP-HALT", [{"tenant_authorized": True, "ambiguous": True, "human_review_required": False, "protected_mutation": False}], LATER)
        self.assertEqual((result.state, result.reason_codes), ("HALTED", ("HUMAN_REVIEW_BYPASS",)))

    def test_containment_disables_feature_and_preserves_manual_review(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        plane.deploy(manifest, _approve(plane, manifest), "OP-HALT", LATER)
        plane.verify_runtime("OP-HALT", [{"tenant_authorized": True, "ambiguous": True, "human_review_required": False, "protected_mutation": False}], LATER)
        state = plane.environment_state()
        self.assertFalse(state["feature_enabled"])
        self.assertTrue(state["manual_review_required"])

    def test_empty_runtime_population_cannot_activate_release(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        plane.deploy(manifest, _approve(plane, manifest), "OP-EMPTY", LATER)
        result = plane.verify_runtime("OP-EMPTY", [], LATER)
        self.assertEqual((result.state, result.reason_codes), ("HALTED", ("RUNTIME_EVIDENCE_MISSING",)))

    def test_cross_tenant_observation_halts_release(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        plane.deploy(manifest, _approve(plane, manifest), "OP-TENANT", LATER)
        result = plane.verify_runtime("OP-TENANT", [{"tenant_authorized": False, "ambiguous": False, "human_review_required": False, "protected_mutation": False}], LATER)
        self.assertIn("TENANT_ISOLATION_VIOLATION", result.reason_codes)

    def test_timeout_after_effect_is_unknown_not_failed(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        decision = plane.deploy(manifest, _approve(plane, manifest), "OP-UNKNOWN", LATER, timeout_after_effect=True)
        self.assertEqual(decision.state, "UNKNOWN_OUTCOME")
        self.assertEqual(plane.environment_state()["release_id"], manifest.release_id)

    def test_unknown_outcome_reconciles_before_retry(self):
        plane, manifest, artifact = self.candidate()
        plane.evaluate(manifest, artifact, LATER)
        plane.deploy(manifest, _approve(plane, manifest), "OP-UNKNOWN", LATER, timeout_after_effect=True)
        decision = plane.reconcile_unknown("OP-UNKNOWN", LATER)
        self.assertEqual(decision.state, "VERIFYING")
        self.assertEqual([row["state"] for row in plane.operation_events("OP-UNKNOWN")], ["AUTHORIZED", "DISPATCHED", "UNKNOWN_OUTCOME", "VERIFYING"])

    def test_image_only_rollback_is_incomplete(self):
        plane, manifest, artifact = self.candidate(release_id="AI-2500-R16")
        plane.evaluate(manifest, artifact, LATER)
        restored = dict(manifest.dependencies)
        restored["prompt_digest"] = "sha256:prompt-v8"
        result = plane.recover("INC-1", "FAILED", manifest, restored, (), (), LATER)
        self.assertEqual(result.state, "RECOVERY_INCOMPLETE")
        self.assertIn("COMPONENT_NOT_RESTORED:prompt_digest", result.reason_codes)

    def test_open_business_reconciliation_prevents_recovered(self):
        plane, manifest, artifact = self.candidate(release_id="AI-2500-R16")
        plane.evaluate(manifest, artifact, LATER)
        result = plane.recover(
            "INC-2", "FAILED", manifest, manifest.dependencies,
            ("manual_review_restored", "unauthorized_mutations_disabled", "production_health_checks"),
            ("historical_submission_audit",), LATER,
        )
        self.assertEqual(result.state, "RECOVERY_IN_PROGRESS")

    def test_complete_identity_and_reconciliation_can_recover(self):
        plane, manifest, artifact = self.candidate(release_id="AI-2500-R16")
        plane.evaluate(manifest, artifact, LATER)
        result = plane.recover(
            "INC-3", "FAILED", manifest, manifest.dependencies,
            ("manual_review_restored", "unauthorized_mutations_disabled", "production_health_checks"), (), LATER,
        )
        self.assertEqual(result.state, "RECOVERED")
        self.assertEqual(plane.environment_state()["release_id"], manifest.release_id)

    def test_recovery_target_must_be_verified(self):
        plane, manifest, _ = self.candidate(release_id="AI-2500-R16")
        self.assertReleaseError(
            "RECOVERY_TARGET_UNTRUSTED",
            lambda: plane.recover("INC-UNTRUSTED", "AI-2500-R17", manifest, manifest.dependencies, (), (), LATER),
        )

    def test_release_states_include_uncertainty_and_recovery(self):
        self.assertTrue({"FAILED", "UNKNOWN_OUTCOME", "RECOVERY_INCOMPLETE", "RECOVERY_IN_PROGRESS", "RECOVERED"} <= RELEASE_STATES)

    def test_valid_reference_reaches_active_with_exact_digest(self):
        result = valid_release(SCENARIO, self.directory.name)
        self.assertEqual(result["state"], "ACTIVE")
        self.assertEqual(result["artifact_digest"], result["deployed_digest"])
        self.assertTrue(result["manual_review_required"])

    def test_golden_population_is_twelve(self):
        report = run_golden_scenarios(SCENARIO)
        self.assertEqual((report["passed"], report["total"]), (12, 12))

    def test_adversarial_population_is_twelve(self):
        report = run_adversarial_evaluations(SCENARIO)
        self.assertEqual((report["passed"], report["total"]), (12, 12))

    def test_report_stops_at_accountable_review(self):
        report = run_reference(SCENARIO)
        self.assertEqual(report["decision"], "ELIGIBLE_FOR_ACCOUNTABLE_REVIEW")
        self.assertGreaterEqual(len(report["non_authorities"]), 3)

    def test_scenario_labels_are_not_evaluator_inputs(self):
        source = (SCENARIO / "release_app/simulation.py").read_text(encoding="utf-8")
        self.assertNotIn("scenarios/", source)
        self.assertNotIn("evaluation-cases.json", source)

    def test_workshop_has_seven_decisions_and_complete_reference(self):
        starter = json.loads((SCENARIO / "workshop/starter/release-design.json").read_text())
        reference = json.loads((SCENARIO / "reference/release-design.json").read_text())
        self.assertEqual(len(starter["learner_decisions"]), 7)
        self.assertNotIn("TODO", json.dumps(reference))

    def test_documented_scenarios_are_twelve_json_files(self):
        self.assertEqual(len(list((SCENARIO / "scenarios").glob("*.json"))), 12)

    def test_policy_inputs_are_resolved_by_application_not_agent_flags(self):
        source = (SCENARIO / "release_app/control_plane.py").read_text(encoding="utf-8")
        self.assertNotIn("candidate[\"build_provenance_valid\"]", source)
        self.assertIn("EVIDENCE_PRODUCER_UNTRUSTED", source)


if __name__ == "__main__":
    unittest.main()
