"""Focused invariants for Course 27 quality engineering and verification."""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "curriculum/advanced/03-testing-quality-agentic-sdd/northstar-quality-control"
sys.path.insert(0, str(SCENARIO))

from quality_app.control_plane import QualityControlPlane  # noqa: E402
from quality_app.evaluation_engine import compare_models, load_jsonl  # noqa: E402
from quality_app.models import QualityError  # noqa: E402
from quality_app.mutation_runner import MUTATION_TO_CHECK  # noqa: E402
from quality_app.oracle_registry import OracleRegistry  # noqa: E402
from quality_app.registry import digest_payload, sign_payload  # noqa: E402
from quality_app.simulation import (  # noqa: E402
    ADVERSARIAL_CASES,
    EXTRA_SCENARIOS,
    GOLDEN,
    demonstrate_subject_tamper,
    quality_context,
    run_evaluation,
    run_golden,
    run_reference,
    run_scenario_in_context,
)
from quality_app.test_selector import select_tests  # noqa: E402


class Course27Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manager = quality_context(SCENARIO)
        cls.context = cls.manager.__enter__()
        cls.plane: QualityControlPlane = cls.context["plane"]
        cls.subject = cls.context["subject"]
        cls.record = cls.context["evidence"]
        cls.observations = cls.context["observations"]

    @classmethod
    def tearDownClass(cls):
        cls.manager.__exit__(None, None, None)

    def scenario(self, scenario_id: str):
        return run_scenario_in_context(self.context, scenario_id)

    def test_active_policy_is_external_and_current(self):
        self.assertEqual(self.plane.policy_version, "QUALITY-POLICY@2")
        self.assertEqual(self.plane.policy["suite_revision"], "NORTHSTAR-QUALITY-SUITE@2")

    def test_oracle_registry_has_five_protected_invariants(self):
        registry = OracleRegistry(SCENARIO)
        self.assertEqual(registry.requirement_ids, {"QI-001", "QI-002", "QI-003", "QI-004", "QI-005"})

    def test_oracle_registry_has_seventeen_requirement_kind_pairs(self):
        self.assertEqual(len(OracleRegistry(SCENARIO).required_pairs()), 17)

    def test_revision_set_contains_three_full_git_commits(self):
        commits = dict(self.subject.component_commits)
        self.assertEqual(set(commits), {"ai-service", "review-service", "underwriting-api"})
        self.assertTrue(all(len(revision) == 40 for revision in commits.values()))

    def test_git_revision_fixture_is_reproducible(self):
        reference = run_reference(SCENARIO)
        self.assertEqual(reference["revision_set"], dict(self.subject.component_commits))

    def test_evidence_binds_contract_dataset_and_oracle_digests(self):
        self.assertTrue(self.subject.contract_digest.startswith("sha256:"))
        self.assertTrue(self.subject.dataset_digest.startswith("sha256:"))
        self.assertTrue(self.subject.oracle_digest.startswith("sha256:"))

    def test_clean_actual_behavior_is_conformant(self):
        self.assertEqual(self.scenario("clean-candidate")["decision"], "CONFORMANT")

    def test_quality_report_never_authorizes_delivery(self):
        report = self.plane.evaluate(self.subject, [self.record], "2026-11-08T18:00:00Z")
        self.assertFalse(report.merge_authorized)
        self.assertFalse(report.deployment_authorized)
        self.assertFalse(report.activation_authorized)
        self.assertFalse(report.release_authorized)
        self.assertEqual(report.delivery_state, "READY_FOR_INTEGRATION_REVIEW")

    def test_ambiguity_property_and_metamorphic_populations(self):
        self.assertEqual(self.observations["property"]["population"], 101)
        self.assertTrue(self.observations["property"]["passed"])
        self.assertEqual(self.observations["metamorphic"]["population"], 3)
        self.assertTrue(self.observations["metamorphic"]["passed"])

    def test_cross_tenant_access_is_denied(self):
        self.assertTrue(self.observations["behavior"]["checks"]["cross_tenant_denied"])

    def test_ai_service_cannot_mutate_authoritative_state(self):
        self.assertTrue(self.observations["behavior"]["checks"]["ai_cannot_mutate_state"])

    def test_concurrent_duplicate_has_one_durable_effect(self):
        behavior = self.observations["behavior"]
        self.assertEqual(behavior["concurrent_statuses"], ["APPLIED", "REPLAYED"])
        self.assertEqual(behavior["effect_count"], 1)

    def test_conflicting_idempotency_payload_is_rejected(self):
        self.assertEqual(self.observations["behavior"]["conflict_status"], "IDEMPOTENCY_CONFLICT")

    def test_expired_and_revoked_approvals_are_rejected(self):
        checks = self.observations["behavior"]["checks"]
        self.assertTrue(checks["expired_approval_rejected"])
        self.assertTrue(checks["revoked_approval_rejected"])

    def test_review_outage_preserves_safe_state(self):
        self.assertEqual(
            self.observations["behavior"]["outage_status"],
            "REVIEW_UNAVAILABLE_SAFE_HOLD",
        )

    def test_unsupported_evidence_reference_is_rejected_by_behavior(self):
        self.assertTrue(self.observations["behavior"]["checks"]["unsupported_evidence_rejected"])

    def test_all_policy_selected_mutants_are_killed(self):
        mutations = self.observations["mutations"]
        self.assertEqual(len(mutations), 7)
        self.assertEqual({item["mutation_id"] for item in mutations}, set(MUTATION_TO_CHECK))
        self.assertTrue(all(item["outcome"] == "KILLED" for item in mutations))

    def test_mutation_denominator_is_not_inflated(self):
        report = self.plane.evaluate(self.subject, [self.record], "2026-11-08T18:00:00Z")
        self.assertEqual(report.metrics["mutation"], {
            "killed": 7,
            "required": 7,
            "value": 1.0,
            "excluded_from_denominator": 0,
        })

    def test_six_failure_experiments_reach_safe_states(self):
        faults = self.observations["fault_experiments"]
        self.assertEqual(len(faults), 6)
        self.assertTrue(all(item["outcome"] == "SAFE" for item in faults))

    def test_model_v2_improves_fixture_accuracy_but_is_blocked(self):
        comparison = compare_models(SCENARIO)
        v1 = comparison["holdout"]["v1"]
        v2 = comparison["holdout"]["v2"]
        self.assertGreater(v2["accuracy"]["value"], v1["accuracy"]["value"])
        self.assertEqual(v1["decision"], "CONFORMANT")
        self.assertEqual(v2["decision"], "BLOCKED")

    def test_model_v2_reports_protected_slice_failures(self):
        violations = compare_models(SCENARIO)["holdout"]["v2"]["protected_violations"]
        self.assertIn("HOLD-005:REVIEW_ROUTING_BYPASS", violations)
        self.assertIn("HOLD-008:UNSUPPORTED_EVIDENCE", violations)

    def test_overfit_candidate_fails_independent_holdout(self):
        comparison = compare_models(SCENARIO)
        self.assertEqual(comparison["development"]["overfit"]["accuracy"]["value"], 1.0)
        self.assertEqual(comparison["holdout"]["overfit"]["accuracy"], {
            "numerator": 2,
            "denominator": 8,
            "value": 0.25,
        })

    def test_evaluation_reports_per_class_precision_and_recall(self):
        per_class = compare_models(SCENARIO)["holdout"]["v2"]["per_class"]
        self.assertEqual(set(per_class), {"APPLICATION", "LOSS_HISTORY", "OTHER", "POLICY"})
        self.assertTrue(all("precision" in value and "recall" in value for value in per_class.values()))

    def test_evaluation_labels_have_owner_and_revision(self):
        rows = load_jsonl(SCENARIO / "datasets/protected-holdout.jsonl")
        self.assertTrue(all(item["label_owner"] == "Underwriting Quality" for item in rows))
        self.assertTrue(all(item["label_revision"] == 3 for item in rows))

    def test_authorization_change_selects_protected_negative_tests(self):
        selection = select_tests({
            "category": "authorization",
            "protected_boundaries": ["tenant_isolation", "state_authority"],
            "unknown_dependencies": False,
        })
        self.assertEqual(selection["status"], "READY")
        self.assertTrue({"security", "negative", "contract", "integration"}.issubset(selection["selected_kinds"]))

    def test_unknown_impact_requires_review_and_keeps_mandatory_tests(self):
        selection = select_tests({
            "category": "shared_api",
            "protected_boundaries": ["human_review"],
            "unknown_dependencies": True,
        })
        self.assertEqual(selection["status"], "IMPACT_REVIEW_REQUIRED")
        self.assertIn("property", selection["selected_kinds"])
        self.assertFalse(selection["unknown_impact_is_no_impact"])

    def test_candidate_tests_are_diagnostic_only(self):
        self.assertEqual(self.scenario("candidate-only")["decision"], "INSUFFICIENT_EVIDENCE")

    def test_forged_evidence_is_insufficient(self):
        result = self.scenario("forged-evidence")
        self.assertEqual(result["decision"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("EVIDENCE_AUTHENTICITY_UNVERIFIED", result["finding_codes"])

    def test_stale_subject_is_explicit(self):
        self.assertEqual(self.scenario("stale-subject")["decision"], "STALE_EVIDENCE")

    def test_stale_suite_and_policy_are_explicit(self):
        self.assertEqual(self.scenario("stale-suite")["decision"], "STALE_EVIDENCE")
        self.assertEqual(self.scenario("stale-policy")["decision"], "STALE_EVIDENCE")

    def test_flaky_protected_test_requires_review(self):
        result = self.scenario("flaky-protected-test")
        self.assertEqual(result["decision"], "REVIEW_REQUIRED")
        self.assertIn("FLAKY_TEST_NOT_EVIDENCE", result["finding_codes"])

    def test_deleted_mandatory_test_is_insufficient(self):
        self.assertEqual(self.scenario("mandatory-test-deleted")["decision"], "INSUFFICIENT_EVIDENCE")

    def test_weakened_oracle_is_insufficient(self):
        self.assertEqual(self.scenario("oracle-weakened")["decision"], "INSUFFICIENT_EVIDENCE")

    def test_surviving_critical_mutant_blocks(self):
        result = self.scenario("ambiguity-bypass")
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("CRITICAL_MUTANT_SURVIVED", result["finding_codes"])

    def test_unsafe_fault_experiment_blocks(self):
        result = self.scenario("unsafe-review-outage")
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("FAILURE_EXPERIMENT_UNSAFE", result["finding_codes"])

    def test_missing_fault_experiment_is_insufficient(self):
        self.assertEqual(self.scenario("missing-failure-experiment")["decision"], "INSUFFICIENT_EVIDENCE")

    def test_unknown_requirement_reference_blocks(self):
        self.assertEqual(self.scenario("unknown-requirement")["decision"], "BLOCKED")

    def test_evidence_id_collision_blocks(self):
        self.assertEqual(self.scenario("evidence-id-collision")["decision"], "BLOCKED")

    def test_malformed_authenticated_evidence_is_insufficient(self):
        self.assertEqual(self.scenario("malformed-evidence")["decision"], "INSUFFICIENT_EVIDENCE")

    def test_subject_signature_is_required(self):
        forged = replace(self.subject, signature="hmac-sha256:forged")
        with self.assertRaises(QualityError) as caught:
            self.plane.evaluate(forged, [], "2026-11-08T18:00:00Z")
        self.assertEqual(caught.exception.code, "SUBJECT_AUTHENTICITY_UNVERIFIED")

    def test_subject_digest_changes_with_any_component_revision(self):
        changed = replace(self.subject, component_commits=(("ai-service", "f" * 40), *self.subject.component_commits[1:]))
        self.assertNotEqual(digest_payload(self.subject.payload()), digest_payload(changed.payload()))

    def test_subject_tamper_is_rejected(self):
        self.assertEqual(demonstrate_subject_tamper(SCENARIO), "SUBJECT_AUTHENTICITY_UNVERIFIED")

    def test_all_fifteen_golden_scenarios_match(self):
        results = run_golden(SCENARIO, self.context)
        self.assertEqual(len(results), 15)
        self.assertTrue(all(item["passed"] for item in results))

    def test_adversarial_evaluation_has_forty_two_cases(self):
        evaluation = run_evaluation(SCENARIO, self.context)
        self.assertEqual(len(evaluation["cases"]), 42)
        self.assertEqual(evaluation["metrics"]["exact_decision_accuracy"], {
            "numerator": 42,
            "denominator": 42,
            "value": 1.0,
        })

    def test_adversarial_evaluation_reports_clean_false_positives(self):
        metric = run_evaluation(SCENARIO, self.context)["metrics"]["clean_control_false_positives"]
        self.assertEqual(metric, {"numerator": 0, "denominator": 3, "value": 0.0})

    def test_static_golden_registry_matches_executable_registry(self):
        registry = json.loads((SCENARIO / "conformance-suite.json").read_text())
        self.assertEqual({item["id"] for item in registry["scenarios"]}, set(GOLDEN))

    def test_static_adversarial_registry_matches_executable_registry(self):
        registry = json.loads((SCENARIO / "evaluation-cases.json").read_text())
        self.assertEqual(
            [(item["case_id"], item["scenario"]) for item in registry["cases"]],
            ADVERSARIAL_CASES,
        )

    def test_report_contract_declares_all_decision_states(self):
        contract = json.loads((SCENARIO / "contracts/quality-report.schema.json").read_text())
        decisions = set(contract["properties"]["decision"]["enum"])
        self.assertTrue({"CONFORMANT", "BLOCKED", "INSUFFICIENT_EVIDENCE", "REVIEW_REQUIRED", "STALE_EVIDENCE", "CONFORMANT_WITH_EXCEPTION"}.issubset(decisions))

    def test_service_contracts_are_machine_readable(self):
        for name in ("classification-v3.schema.json", "review-state.schema.json"):
            contract = json.loads((SCENARIO / "contracts" / name).read_text())
            self.assertEqual(contract["type"], "object")

    def test_six_scenario_artifacts_exist(self):
        self.assertEqual(len(list((SCENARIO / "scenarios").glob("*.json"))), 6)

    def test_optional_hypothesis_path_is_documented(self):
        dependencies = (SCENARIO / "optional-tools.txt").read_text()
        self.assertIn("pytest", dependencies)
        self.assertIn("hypothesis", dependencies)
        self.assertTrue((SCENARIO / "tests/test_property_hypothesis.py").exists())

    def test_reference_run_stops_at_integration_review(self):
        result = run_reference(SCENARIO)
        self.assertEqual(result["quality_decision"], "CONFORMANT")
        self.assertEqual(result["delivery_state"], "READY_FOR_INTEGRATION_REVIEW")
        self.assertTrue(result["golden_passed"])
        self.assertFalse(result["release_authorized"])

    def test_evaluation_registry_has_expected_scenario_vocabulary(self):
        scenarios = {scenario for _, scenario in ADVERSARIAL_CASES}
        self.assertTrue(scenarios.issubset(set(GOLDEN) | set(EXTRA_SCENARIOS)))

    def test_evidence_signature_changes_when_results_change(self):
        changed = json.loads(json.dumps(self.record))
        changed["payload"]["cases"][0]["runs"] = ["PASS", "PASS"]
        signature = sign_payload(changed["payload"], self.plane.evidence_key)
        self.assertNotEqual(signature, self.record["signature"])


if __name__ == "__main__":
    unittest.main()
